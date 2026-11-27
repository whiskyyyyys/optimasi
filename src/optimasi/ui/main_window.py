"""Main PySide6 window, background worker runner, auto-updater integration, and System Tray."""

from __future__ import annotations

import platform
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from optimasi import APP_NAME, APP_VERSION
from optimasi.core.admin import is_admin, relaunch_as_admin
from optimasi.core.backup import create_restore_point, export_registry_backup, revert_session
from optimasi.core.booster import GameBooster, set_laptop_thermal_mode
from optimasi.core.cleaner import clean_junk, run_system_repair, scan_junk, trim_ram_working_sets
from optimasi.core.executor import TweakExecutor
from optimasi.core.health_score import evaluate_optimization_score
from optimasi.core.system_info import get_net_io_counters, get_system_snapshot, terminate_process
from optimasi.core.updater import UpdateInfo, check_for_updates, load_settings, save_settings
from optimasi.tweaks import (
    ALL_TWEAKS,
    CATEGORIES,
    get_preset_tweaks,
    get_tweaks_by_category,
    search_tweaks,
)
from optimasi.tweaks.models import AppxRemove, DnsSet, RiskLevel, Tweak
from optimasi.tweaks.network_dns import ping_endpoints
from optimasi.tweaks.privacy_debloat import SAFE_BLOAT_APPX, get_installed_bloat_appx
from optimasi.tweaks.startup import set_startup_item_enabled
from optimasi.ui.custom_widgets import ToggleSwitch, UpdateBanner, UpdateDialog
from optimasi.ui.style import DARK_QSS, apply_windows_dark_titlebar
from optimasi.ui.views import (
    BackupUpdatesView,
    BoosterView,
    CategoryView,
    CleanerView,
    DashboardView,
)


def resolve_asset_path(relative_path: str) -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / relative_path,
        Path(__file__).resolve().parents[2] / relative_path,
        Path(sys.executable).resolve().parent / relative_path,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, Path(meipass) / relative_path)
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


class _TaskWorker(QThread):
    log_line = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[[Callable[[str], None]], Any]):
        super().__init__()
        self.fn = fn

    def run(self) -> None:
        try:
            res = self.fn(self.log_line.emit)
            self.done.emit(res)
        except Exception as exc:
            self.failed.emit(str(exc))


class _UpdateCheckWorker(QThread):
    completed = Signal(object, object)  # (UpdateInfo | None, err | None)

    def run(self) -> None:
        info, err = check_for_updates()
        self.completed.emit(info, err)


class MainWindow(QMainWindow):
    """Commercial-grade Fluent PySide6 window for Optimasi Windows."""

    NAV_ITEMS = [
        ("dashboard", "🏠  Dashboard"),
        ("booster", "⚡  Game & Laptop Booster"),
        ("CPU & Power", "🧠  CPU & Power"),
        ("GPU & Gaming", "🎮  GPU & Gaming"),
        ("Network & DNS", "🌐  Network & DNS"),
        ("Privacy & Debloat", "🛡  Privacy & Debloat"),
        ("RAM & Storage", "💾  RAM & Storage"),
        ("Services & System", "⚙  Services & System"),
        ("cleaner", "🧹  Cleaner & Repair"),
        ("backup", "🔄  Backup & Updates"),
    ]

    def __init__(self, start_dry_run: bool = False, enable_auto_update: bool = True):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1260, 810)
        self.setMinimumSize(1060, 680)

        icon_path = resolve_asset_path("assets/app.ico")
        self.app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)

        self.dry_run = start_dry_run
        self.settings = load_settings()
        self.booster = GameBooster()
        self.latest_update: UpdateInfo | None = None
        self.active_workers: list[QThread] = []
        self._force_quit = False

        self.tweak_checked: dict[str, bool] = {t.id: t.default_selected for t in ALL_TWEAKS}
        self.appx_checked: dict[str, bool] = {pkg: True for pkg, _ in SAFE_BLOAT_APPX}
        self._last_net_io = get_net_io_counters()
        self._last_net_time = time.monotonic()

        self._build_ui()
        self._setup_tray()
        apply_windows_dark_titlebar(int(self.winId()))

        self._refresh_hardware_and_score()
        self._start_telemetry_timer()

        if enable_auto_update and self.settings.get("auto_check_updates", True):
            QTimer.singleShot(1200, lambda: self.check_updates_async(manual=False))

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_lay = QHBoxLayout(root)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(236)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 18, 12, 14)
        sb_lay.setSpacing(4)

        brand = QLabel("OPTIMASI")
        brand.setObjectName("BrandTitle")
        sb_lay.addWidget(brand)
        sub = QLabel(f"Windows Suite • v{APP_VERSION}")
        sub.setObjectName("BrandSub")
        sb_lay.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #1C263B; max-height: 1px; margin: 8px 0px;")
        sb_lay.addWidget(sep)

        self.nav_buttons: dict[str, QPushButton] = {}
        for page_id, label in self.NAV_ITEMS:
            btn = QPushButton(label)
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, pid=page_id: self.switch_page(pid))
            sb_lay.addWidget(btn)
            self.nav_buttons[page_id] = btn

        sb_lay.addStretch()

        self.sidebar_footer = QLabel(
            f"Python {platform.python_version()} • Nuitka Ready\n{len(ALL_TWEAKS)} Optimizations Loaded"
        )
        self.sidebar_footer.setStyleSheet("color: #64748B; font-size: 11px; padding: 6px;")
        sb_lay.addWidget(self.sidebar_footer)
        main_lay.addWidget(sidebar)

        # Right Column (Header + UpdateBanner + Stack + Console)
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        # Header Bar
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(60)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 10, 20, 10)
        h_lay.setSpacing(12)

        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        h_lay.addWidget(self.page_title)
        h_lay.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Cari tweak (Nagle, HAGS, Copilot, Ryzen, SSD)...")
        self.search_box.setFixedWidth(300)
        self.search_box.textChanged.connect(self._on_search)
        h_lay.addWidget(self.search_box)

        dry_lbl = QLabel("Dry-Run")
        dry_lbl.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
        h_lay.addWidget(dry_lbl)
        self.dry_switch = ToggleSwitch(checked=self.dry_run, accent="#F59E0B")
        self.dry_switch.toggled.connect(self._on_dry_run_toggled)
        h_lay.addWidget(self.dry_switch)

        admin_ok = is_admin()
        self.admin_btn = QPushButton("ADMIN AKTIF" if admin_ok else "ELEVATE (ADMIN)")
        self.admin_btn.setObjectName("SuccessBtn" if admin_ok else "WarningBtn")
        self.admin_btn.clicked.connect(self._on_elevate if not admin_ok else lambda: self.log("Sudah berjalan dengan hak Administrator."))
        h_lay.addWidget(self.admin_btn)
        right_col.addWidget(header)

        # In-App Update Notification Banner
        banner_wrap = QVBoxLayout()
        banner_wrap.setContentsMargins(20, 8, 20, 0)
        self.update_banner = UpdateBanner()
        self.update_banner.details_clicked.connect(self._open_update_dialog)
        self.update_banner.update_clicked.connect(self._open_update_dialog_and_download)
        banner_wrap.addWidget(self.update_banner)
        right_col.addLayout(banner_wrap)

        # Console Drawer (built before views so status_lbl & console always exist)
        console_wrap = QFrame()
        console_wrap.setStyleSheet("background-color: #0E1422; border-top: 1px solid #1C263B;")
        c_lay = QVBoxLayout(console_wrap)
        c_lay.setContentsMargins(16, 6, 16, 10)
        c_lay.setSpacing(4)

        cbar = QHBoxLayout()
        cbar.addWidget(QLabel("EXECUTION LOG", styleSheet="font-size: 10px; font-weight: 700; color: #94A3B8;"))
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #22D3EE; margin-left: 10px;")
        cbar.addWidget(self.status_lbl)
        cbar.addStretch()
        btn_toggle_con = QPushButton("Hide/Show")
        btn_toggle_con.setObjectName("GhostBtn")
        btn_toggle_con.clicked.connect(lambda: self.console.setVisible(not self.console.isVisible()))
        cbar.addWidget(btn_toggle_con)
        btn_clear_con = QPushButton("Clear")
        btn_clear_con.setObjectName("GhostBtn")
        btn_clear_con.clicked.connect(lambda: self.console.clear())
        cbar.addWidget(btn_clear_con)
        c_lay.addLayout(cbar)

        self.console = QPlainTextEdit()
        self.console.setObjectName("ConsoleBox")
        self.console.setReadOnly(True)
        self.console.setFixedHeight(105)
        c_lay.addWidget(self.console)

        # Page Router
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView(self)
        self.booster_view = BoosterView(self)
        self.category_view = CategoryView(self)
        self.cleaner_view = CleanerView(self)
        self.backup_view = BackupUpdatesView(self)

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.booster_view)
        self.stack.addWidget(self.category_view)
        self.stack.addWidget(self.cleaner_view)
        self.stack.addWidget(self.backup_view)
        right_col.addWidget(self.stack, 1)
        right_col.addWidget(console_wrap)

        main_lay.addLayout(right_col, 1)
        self.switch_page("dashboard")
        self.log(f"{APP_NAME} v{APP_VERSION} siap. Dry-Run: {'ON' if self.dry_run else 'OFF'}.")

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip(f"{APP_NAME} v{APP_VERSION}")

        menu = QMenu()
        act_open = QAction("Buka Optimasi Windows", self)
        act_open.triggered.connect(self._restore_from_tray)
        menu.addAction(act_open)

        act_trim = QAction("⚡ Quick RAM Trim", self)
        act_trim.triggered.connect(self.trim_ram_now)
        menu.addAction(act_trim)

        act_boost = QAction("🎮 Toggle Game Boost", self)
        act_boost.triggered.connect(self.toggle_game_boost)
        menu.addAction(act_boost)

        act_upd = QAction("🔄 Cek Update GitHub", self)
        act_upd.triggered.connect(lambda: self.check_updates_async(manual=True))
        menu.addAction(act_upd)

        menu.addSeparator()
        act_exit = QAction("Keluar", self)
        act_exit.triggered.connect(self._quit_completely)
        menu.addAction(act_exit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def shutdown(self) -> None:
        """Stop timers and wait cleanly for background QThreads before exit."""
        self._force_quit = True
        if hasattr(self, "telemetry_timer"):
            self.telemetry_timer.stop()
        app = QApplication.instance()
        for w in list(self.active_workers):
            while w.isRunning():
                if app:
                    app.processEvents()
                if w.wait(100):
                    break
        self.active_workers.clear()
        if getattr(self, "tray", None):
            self.tray.hide()

    def _quit_completely(self) -> None:
        self.shutdown()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if (
            not self._force_quit
            and self.tray is not None
            and self.settings.get("minimize_to_tray", True)
        ):
            event.ignore()
            self.hide()
            self.tray.showMessage(
                APP_NAME,
                "Aplikasi berjalan di System Tray. Klik kanan ikon untuk Quick RAM Trim atau Exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2500,
            )
            return
        self.shutdown()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Logging, Settings, & Background Runner
    # ------------------------------------------------------------------
    def log(self, msg: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, "console"):
            self.console.appendPlainText(f"[{stamp}] {msg}")

    def update_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        save_settings(self.settings)

    def _on_dry_run_toggled(self, val: bool) -> None:
        self.dry_run = val
        self.log(f"Dry-Run Mode {'AKTIF (simulasi aman)' if val else 'NONAKTIF (eksekusi live)'}.")

    def _on_elevate(self) -> None:
        self.log("Meminta hak Administrator (UAC)...")
        if relaunch_as_admin():
            self._quit_completely()
        else:
            self.log("Elevasi UAC dibatalkan atau gagal.")

    def _run_bg(
        self,
        label: str,
        fn: Callable[[Callable[[str], None]], Any],
        on_done: Callable[[Any], None] | None = None,
    ) -> None:
        if hasattr(self, "status_lbl"):
            self.status_lbl.setText(f"Running: {label}...")
        worker = _TaskWorker(fn)
        worker.log_line.connect(self.log)

        def _ok(res: Any) -> None:
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Ready")
            if on_done:
                on_done(res)
            if worker in self.active_workers:
                self.active_workers.remove(worker)

        def _err(err: str) -> None:
            if hasattr(self, "status_lbl"):
                self.status_lbl.setText("Ready")
            self.log(f"ERROR ({label}): {err}")
            if worker in self.active_workers:
                self.active_workers.remove(worker)

        worker.done.connect(_ok)
        worker.failed.connect(_err)
        self.active_workers.append(worker)
        worker.start()

    # ------------------------------------------------------------------
    # Navigation & Search
    # ------------------------------------------------------------------
    def switch_page(self, page_id: str) -> None:
        for pid, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if pid == page_id else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        titles = dict(self.NAV_ITEMS)
        raw_title = titles.get(page_id, page_id)
        self.page_title.setText(raw_title.split("  ", 1)[-1])

        if page_id == "dashboard":
            self.stack.setCurrentWidget(self.dashboard_view)
        elif page_id == "booster":
            self.booster_view.refresh_processes()
            self.stack.setCurrentWidget(self.booster_view)
        elif page_id == "cleaner":
            if not self.cleaner_view._scanned_once:
                self.cleaner_view.refresh_scan()
            self.stack.setCurrentWidget(self.cleaner_view)
        elif page_id == "backup":
            self.backup_view.refresh_sessions()
            self.stack.setCurrentWidget(self.backup_view)
        elif page_id in CATEGORIES:
            self.category_view.load_tweaks(page_id, get_tweaks_by_category(page_id), mode=page_id)
            self.stack.setCurrentWidget(self.category_view)

    def _on_search(self, text: str) -> None:
        q = text.strip()
        if not q:
            self.switch_page("dashboard")
            return
        matches = search_tweaks(q)
        self.page_title.setText(f"Search: '{q}'")
        self.category_view.load_tweaks(f"Hasil Pencarian '{q}'", matches, mode="")
        self.stack.setCurrentWidget(self.category_view)

    # ------------------------------------------------------------------
    # Live Telemetry & Health Score
    # ------------------------------------------------------------------
    def _refresh_hardware_and_score(self) -> None:
        def _work(_log):
            return get_system_snapshot(fast=False), evaluate_optimization_score()

        def _apply(payload) -> None:
            snap, score_data = payload
            os_i = snap["os"]
            cpu = snap["cpu"]
            ram = snap["ram"]
            disk = snap["disk_c"]
            gpus = snap["gpus"]
            bat = snap["battery"]

            device_type = "Laptop" if snap["is_laptop"] else "Desktop"
            gpu_str = gpus[0]["name"] if gpus else "Integrated Graphics"
            self.dashboard_view.device_title.setText(
                f"{snap['manufacturer']} {snap['model']} ({device_type})"
            )
            self.dashboard_view.device_specs.setText(
                f"OS: {os_i['name']} Build {os_i['build']}  •  CPU: {cpu['name']} ({cpu['physical_cores']}C/{cpu['logical_cores']}T)\n"
                f"GPU: {gpu_str}  •  RAM: {ram['total_gb']} GB  •  SSD C: {disk['free_gb']} GB Free / {disk['total_gb']} GB"
            )
            if bat["has_battery"]:
                icon = "🔌" if bat["plugged"] else "🔋"
                state = "Plugged In" if bat["plugged"] else "On Battery"
                self.dashboard_view.battery_pill.setText(f"{icon} Battery {bat['percent']}% ({state})")
            else:
                self.dashboard_view.battery_pill.setText("🖥 AC Desktop Power")
            self.dashboard_view.plan_pill.setText(f"Plan: {snap['power_plan']}")

            self.dashboard_view.disk_val_lbl.setText(f"{disk['free_gb']} GB Free")
            self.dashboard_view.disk_bar.setValue(int(round(disk["percent"])))
            self.dashboard_view.disk_sub_lbl.setText(f"{disk['used_gb']} / {disk['total_gb']} GB ({disk['percent']}%)")

            self.dashboard_view.gauge.set_score(score_data["score"], score_data["grade"])
            self.dashboard_view.score_sub.setText(
                f"Score {score_data['score']}/100 ({score_data['passed_count']}/{score_data['total_count']} checks)"
            )

        self._run_bg("System Scan", _work, on_done=_apply)

    def _start_telemetry_timer(self) -> None:
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.timeout.connect(self._tick_telemetry)
        self.telemetry_timer.start(1500)
        self._tick_telemetry()

    def _tick_telemetry(self) -> None:
        import psutil

        cpu_pct = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()

        now = time.monotonic()
        rx, tx = get_net_io_counters()
        dt = max(0.2, now - self._last_net_time)
        down_kbps = max(0.0, (rx - self._last_net_io[0]) / 1024.0 / dt)
        up_kbps = max(0.0, (tx - self._last_net_io[1]) / 1024.0 / dt)
        self._last_net_io = (rx, tx)
        self._last_net_time = now

        dv = self.dashboard_view
        dv.cpu_val_lbl.setText(f"{cpu_pct:.1f}%")
        dv.cpu_sub_lbl.setText("Real-time processor load")
        dv.cpu_chart.push_value(cpu_pct, 100.0)

        used_gb = round(vm.used / (1024**3), 2)
        tot_gb = round(vm.total / (1024**3), 2)
        dv.ram_val_lbl.setText(f"{vm.percent:.1f}%")
        dv.ram_sub_lbl.setText(f"{used_gb} / {tot_gb} GB used")
        dv.ram_chart.push_value(vm.percent, 100.0)

        dv.net_val_lbl.setText(f"↓ {down_kbps:.0f} KB/s")
        dv.net_sub_lbl.setText(f"↑ {up_kbps:.0f} KB/s upload")
        dv.net_chart.push_value(down_kbps + up_kbps, 2048.0)

    # ------------------------------------------------------------------
    # Auto-Updater Integration
    # ------------------------------------------------------------------
    def check_updates_async(self, manual: bool = False) -> None:
        if manual:
            self.log("Mengecek update terbaru dari GitHub Releases...")
            self.backup_view.update_status_lbl.setText("Sedang mengecek GitHub Releases...")

        worker = _UpdateCheckWorker()

        def _done(info: UpdateInfo | None, err: str | None) -> None:
            if worker in self.active_workers:
                self.active_workers.remove(worker)
            if err:
                self.log(f"Update check note: {err}")
                self.backup_view.update_status_lbl.setText(err)
                return
            if info is None:
                msg = f"Aplikasi sudah versi terbaru (v{APP_VERSION})."
                if manual:
                    self.log(msg)
                self.backup_view.update_status_lbl.setText(msg)
                return

            self.latest_update = info
            self.update_banner.show_update(info)
            self.backup_view.update_status_lbl.setText(
                f"Update tersedia: v{info.latest_version} ({info.asset_name})"
            )
            self.log(f"Update baru ditemukan: v{info.latest_version} — {info.release_name}")
            if self.tray:
                self.tray.showMessage(
                    f"{APP_NAME} — Update Tersedia!",
                    f"Versi v{info.latest_version} tersedia. Buka aplikasi untuk 1-klik update otomatis.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
            if manual:
                self._open_update_dialog()

        worker.completed.connect(_done)
        self.active_workers.append(worker)
        worker.start()

    def _open_update_dialog(self) -> None:
        if not self.latest_update:
            return
        dlg = UpdateDialog(
            self.latest_update,
            dry_run=self.dry_run,
            on_install_started=self._quit_completely,
            parent=self,
        )
        dlg.exec()

    def _open_update_dialog_and_download(self) -> None:
        if not self.latest_update:
            return
        dlg = UpdateDialog(
            self.latest_update,
            dry_run=self.dry_run,
            on_install_started=self._quit_completely,
            parent=self,
        )
        dlg.show()
        dlg.start_download()
        dlg.exec()

    # ------------------------------------------------------------------
    # Actions: Tweaks, Presets, Booster, Cleaner, Backup
    # ------------------------------------------------------------------
    def run_preset(self, preset_id: str, preset_name: str) -> None:
        tweaks = get_preset_tweaks(preset_id)
        dry = self.dry_run

        def _work(log_fn):
            res = TweakExecutor(dry_run=dry, log_cb=log_fn).run_tweaks(tweaks, revert=False, session_label=preset_name)
            log_fn(f"Preset '{preset_name}' selesai: {res.succeeded} OK, {res.failed} gagal, {res.skipped} skip.")

        self._run_bg(preset_name, _work, on_done=lambda _: self._refresh_hardware_and_score())

    def run_single_tweak(self, tweak: Tweak, revert: bool = False) -> None:
        dry = self.dry_run
        mode = "Revert" if revert else "Apply"
        self._run_bg(
            f"{mode} {tweak.name}",
            lambda log_fn: TweakExecutor(dry_run=dry, log_cb=log_fn).run_tweaks([tweak], revert=revert, session_label=tweak.name),
            on_done=lambda _: self._refresh_hardware_and_score(),
        )

    def run_tweaks_batch(self, tweaks: list[Tweak], revert: bool = False) -> None:
        chosen = [t for t in tweaks if self.tweak_checked.get(t.id, False)]
        if not chosen:
            self.log("Tidak ada tweak yang dipilih di halaman ini.")
            return
        dry = self.dry_run
        mode = "Revert" if revert else "Apply"

        def _work(log_fn):
            res = TweakExecutor(dry_run=dry, log_cb=log_fn).run_tweaks(chosen, revert=revert, session_label=f"{mode} {len(chosen)} tweaks")
            log_fn(f"Batch {mode} selesai: {res.succeeded} OK, {res.failed} gagal.")

        self._run_bg(f"{mode} {len(chosen)} tweaks", _work, on_done=lambda _: self._refresh_hardware_and_score())

    def toggle_game_boost(self) -> None:
        dry = self.dry_run
        if self.booster.active:
            self.restore_game_boost()
            return

        def _work(log_fn):
            return self.booster.activate_boost(dry_run=dry, log_cb=log_fn)

        def _done(_res):
            self.booster_view.boost_title.setText("Game & Emulator Booster: ACTIVE ⚡")
            self.booster_view.btn_activate_boost.setText("Boost Aktif (Klik untuk Restore)")
            self._refresh_hardware_and_score()

        self._run_bg("Game Boost", _work, on_done=_done)

    def restore_game_boost(self) -> None:
        dry = self.dry_run

        def _work(log_fn):
            return self.booster.restore_boost(dry_run=dry, log_cb=log_fn)

        def _done(_res):
            self.booster_view.boost_title.setText("Game & Emulator Booster: STANDBY")
            self.booster_view.btn_activate_boost.setText("⚡ Boost Sekarang")
            self._refresh_hardware_and_score()

        self._run_bg("Restore Boost", _work, on_done=_done)

    def apply_thermal_mode(self, mode: str) -> None:
        dry = self.dry_run
        self._run_bg(
            f"Thermal {mode}",
            lambda log_fn: set_laptop_thermal_mode(mode, dry_run=dry, log_cb=log_fn),
        )

    def kill_process(self, pid: int, on_done: Callable[[], None] | None = None) -> None:
        ok, msg = terminate_process(pid, dry_run=self.dry_run)
        self.log(msg)
        if ok and on_done:
            on_done()

    def apply_quick_dns(self, primary: str | None, secondary: str | None, label: str) -> None:
        dry = self.dry_run
        t = Tweak(
            id="quick_dns",
            name=f"Set DNS: {label}",
            category="Network & DNS",
            risk=RiskLevel.SAFE,
            source="Quick DNS",
            description="",
            apply_actions=[DnsSet(primary, secondary, label)],
        )
        self._run_bg(
            f"DNS {label}",
            lambda log_fn: TweakExecutor(dry_run=dry, log_cb=log_fn).run_tweaks([t], session_label=f"DNS {label}"),
        )

    def run_ping_benchmark(self, callback: Callable[[list[dict[str, str]]], None]) -> None:
        def _work(log_fn):
            log_fn("Menjalankan multi-region ping benchmark...")
            rows = ping_endpoints()
            for r in rows:
                log_fn(f"  {r['label']} ({r['ip']}): {r['latency']}")
            return rows

        self._run_bg("Ping Benchmark", _work, on_done=callback)

    def detect_installed_appx(self, callback: Callable[[set[str]], None]) -> None:
        self._run_bg("Detect UWP Apps", lambda _log: get_installed_bloat_appx(), on_done=callback)

    def remove_checked_appx(self) -> None:
        selected = [pkg for pkg, checked in self.appx_checked.items() if checked]
        if not selected:
            self.log("Tidak ada aplikasi UWP yang dicentang.")
            return
        dry = self.dry_run
        t = Tweak(
            id="custom_appx",
            name=f"Remove {len(selected)} UWP Apps",
            category="Privacy & Debloat",
            risk=RiskLevel.MODERATE,
            source="User Selection",
            description="",
            apply_actions=[AppxRemove(selected)],
        )
        self._run_bg(
            "AppX Removal",
            lambda log_fn: TweakExecutor(dry_run=dry, log_cb=log_fn).run_tweaks([t], session_label="AppX Debloat"),
        )

    def toggle_startup(self, hive: str, name: str, enabled: bool) -> None:
        _, msg = set_startup_item_enabled(hive, name, enabled, dry_run=self.dry_run)
        self.log(msg)

    def scan_junk_async(self, callback: Callable[[Any], None]) -> None:
        self._run_bg("Scan Junk", lambda _log: scan_junk(), on_done=callback)

    def clean_junk_async(self, keys: list[str], include_recycle_bin: bool, on_done: Callable[[], None]) -> None:
        if not keys and not include_recycle_bin:
            self.log("Pilih minimal satu kategori sampah.")
            return
        dry = self.dry_run
        self._run_bg(
            "Clean Junk",
            lambda log_fn: clean_junk(keys, include_recycle_bin=include_recycle_bin, dry_run=dry, log_cb=log_fn),
            on_done=lambda _: on_done(),
        )

    def trim_ram_now(self) -> None:
        self._run_bg("Trim RAM", lambda log_fn: trim_ram_working_sets(dry_run=self.dry_run, log_cb=log_fn))

    def run_repair(self, mode: str, title: str) -> None:
        self._run_bg(title, lambda log_fn: run_system_repair(mode, dry_run=self.dry_run, log_cb=log_fn))

    def action_restore_point(self) -> None:
        self._run_bg("Restore Point", lambda log_fn: create_restore_point(dry_run=self.dry_run, log_cb=log_fn))

    def action_backup_registry(self) -> None:
        self._run_bg("Registry Backup", lambda log_fn: export_registry_backup(full=False, dry_run=self.dry_run, log_cb=log_fn))

    def revert_session_path(self, path: str, on_done: Callable[[], None]) -> None:
        self._run_bg(
            "Revert Session",
            lambda log_fn: revert_session(path, dry_run=self.dry_run, log_cb=log_fn),
            on_done=lambda _: on_done(),
        )


def run_gui(start_dry_run: bool = False) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
    app.setQuitOnLastWindowClosed(False)

    win = MainWindow(start_dry_run=start_dry_run)
    win.show()
    return app.exec()
