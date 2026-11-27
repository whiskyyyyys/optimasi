"""All PySide6 application pages (Dashboard, RAM Optimizer, Booster, Categories, Cleaner, Backup & Updates)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optimasi import APP_VERSION
from optimasi.tweaks import PRESETS
from optimasi.tweaks.models import Tweak
from optimasi.tweaks.network_dns import DNS_PRESETS
from optimasi.tweaks.privacy_debloat import SAFE_BLOAT_APPX
from optimasi.ui.custom_widgets import (
    CircularScoreGauge,
    MemoryBreakdownBar,
    SparklineChart,
    ToggleSwitch,
    TweakCardWidget,
)
from optimasi.ui.icons import svg_icon


def _scroll_wrap(widget: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(widget)
    return sa


class DashboardView(QWidget):
    """Hardware Overview, Health Score Gauge, Live Sparklines, and Tailored Presets."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(18)

        # 1. Hero Card + Health Score Gauge
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero_lay = QHBoxLayout(hero)
        hero_lay.setContentsMargins(22, 18, 22, 18)
        hero_lay.setSpacing(20)

        info_col = QVBoxLayout()
        info_col.setSpacing(8)
        self.device_title = QLabel("Mendeteksi Perangkat Windows...")
        self.device_title.setStyleSheet("font-size: 19px; font-weight: 700; color: #FAFAFA;")
        info_col.addWidget(self.device_title)

        self.device_specs = QLabel("Memindai CPU, GPU, RAM & SSD...")
        self.device_specs.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        self.device_specs.setWordWrap(True)
        info_col.addWidget(self.device_specs)

        pills = QHBoxLayout()
        self.battery_pill = QLabel("Power: AC")
        self.battery_pill.setStyleSheet(
            "background-color: rgba(56, 189, 248, 0.14); color: #38BDF8; border-radius: 6px; padding: 3px 10px; font-size: 11px; font-weight: 700;"
        )
        pills.addWidget(self.battery_pill)

        self.plan_pill = QLabel("Plan: Balanced")
        self.plan_pill.setStyleSheet(
            "background-color: rgba(16, 185, 129, 0.14); color: #34D399; border-radius: 6px; padding: 3px 10px; font-size: 11px; font-weight: 600;"
        )
        pills.addWidget(self.plan_pill)
        pills.addStretch()
        info_col.addLayout(pills)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        btn_ram = QPushButton(" Bersihkan RAM")
        btn_ram.setIcon(svg_icon("memory", "#030712", 15))
        btn_ram.setObjectName("PrimaryBtn")
        btn_ram.clicked.connect(self.ctrl.deep_clean_ram_async)
        quick_row.addWidget(btn_ram)

        btn_boost = QPushButton(" Game Boost")
        btn_boost.setIcon(svg_icon("zap", "#34D399", 15))
        btn_boost.setObjectName("SuccessBtn")
        btn_boost.clicked.connect(self.ctrl.toggle_game_boost)
        quick_row.addWidget(btn_boost)

        btn_upd = QPushButton(" Cek Update")
        btn_upd.setIcon(svg_icon("download", "#E4E4E7", 15))
        btn_upd.setObjectName("GhostBtn")
        btn_upd.clicked.connect(lambda: self.ctrl.check_updates_async(manual=True))
        quick_row.addWidget(btn_upd)

        btn_restore = QPushButton(" Restore Point")
        btn_restore.setIcon(svg_icon("shield", "#E4E4E7", 15))
        btn_restore.setObjectName("GhostBtn")
        btn_restore.clicked.connect(self.ctrl.action_restore_point)
        quick_row.addWidget(btn_restore)
        quick_row.addStretch()
        info_col.addLayout(quick_row)

        hero_lay.addLayout(info_col, 1)

        gauge_col = QVBoxLayout()
        gauge_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gauge = CircularScoreGauge(subtitle_prefix="GRADE")
        gauge_col.addWidget(self.gauge, 0, Qt.AlignmentFlag.AlignCenter)
        self.score_sub = QLabel("Optimization Score")
        self.score_sub.setStyleSheet("color: #A1A1AA; font-size: 11px; font-weight: 600;")
        self.score_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gauge_col.addWidget(self.score_sub)
        hero_lay.addLayout(gauge_col)

        lay.addWidget(hero)

        # 2. Live Telemetry Sparkline Row
        tel_row = QHBoxLayout()
        tel_row.setSpacing(14)

        self.cpu_val_lbl, self.cpu_sub_lbl, self.cpu_chart, c1 = self._make_spark_card("CPU LOAD", "#38BDF8")
        self.ram_val_lbl, self.ram_sub_lbl, self.ram_chart, c2 = self._make_spark_card("MEMORY (RAM)", "#8B5CF6")
        self.net_val_lbl, self.net_sub_lbl, self.net_chart, c3 = self._make_spark_card("NETWORK I/O", "#10B981")

        c4 = QFrame()
        c4.setObjectName("Card")
        dlay = QVBoxLayout(c4)
        dlay.setContentsMargins(16, 14, 16, 14)
        dlay.addWidget(QLabel("SYSTEM DISK (C:)", styleSheet="font-size: 10px; font-weight: 700; color: #71717A;"))
        self.disk_val_lbl = QLabel("—")
        self.disk_val_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #F59E0B;")
        dlay.addWidget(self.disk_val_lbl)
        self.disk_bar = QProgressBar()
        self.disk_bar.setValue(0)
        dlay.addWidget(self.disk_bar)
        self.disk_sub_lbl = QLabel("—")
        self.disk_sub_lbl.setStyleSheet("font-size: 11px; color: #A1A1AA;")
        dlay.addWidget(self.disk_sub_lbl)

        for card in (c1, c2, c3, c4):
            tel_row.addWidget(card, 1)
        lay.addLayout(tel_row)

        # 3. Curated One-Click Presets
        sec_hdr = QLabel("One-Click Optimization Profiles (Disesuaikan dengan Spek Laptopmu)")
        sec_hdr.setStyleSheet("font-size: 15px; font-weight: 700; color: #FAFAFA; margin-top: 4px;")
        lay.addWidget(sec_hdr)

        self.preset_grid = QGridLayout()
        self.preset_grid.setSpacing(14)
        self.preset_cards: dict[str, QFrame] = {}
        preset_icons = {
            "laptop_pro": "cpu",
            "laptop_battery": "shield",
            "gaming_pro": "zap",
            "safe_daily": "check",
        }
        for idx, preset in enumerate(PRESETS):
            pcard = QFrame()
            pcard.setObjectName("FeaturedPresetCard" if preset.id == "laptop_pro" else "Card")
            play = QVBoxLayout(pcard)
            play.setContentsMargins(18, 16, 18, 16)
            play.setSpacing(8)

            badge_row = QHBoxLayout()
            badge_row.setSpacing(6)
            b_ico = QLabel()
            b_ico.setPixmap(svg_icon(preset_icons.get(preset.id, "sparkles"), "#38BDF8", 14).pixmap(14, 14))
            badge_row.addWidget(b_ico)
            badge = QLabel(preset.badge)
            badge.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;")
            badge_row.addWidget(badge)
            badge_row.addStretch()
            play.addLayout(badge_row)

            pname = QLabel(preset.name)
            pname.setStyleSheet("color: #FAFAFA; font-size: 15px; font-weight: 700;")
            play.addWidget(pname)

            pdesc = QLabel(f"{preset.description}\n({len(preset.tweak_ids)} tweaks)")
            pdesc.setStyleSheet("color: #A1A1AA; font-size: 12px;")
            pdesc.setWordWrap(True)
            play.addWidget(pdesc, 1)

            btn = QPushButton(f"Apply {preset.name}")
            btn.setObjectName("PrimaryBtn" if preset.id in ("laptop_pro", "gaming_pro") else "SuccessBtn")
            btn.clicked.connect(lambda _=False, pid=preset.id, nm=preset.name: self.ctrl.run_preset(pid, nm))
            play.addWidget(btn)

            self.preset_cards[preset.id] = pcard
            self.preset_grid.addWidget(pcard, idx // 2, idx % 2)

        lay.addLayout(self.preset_grid)
        lay.addStretch()
        outer.addWidget(_scroll_wrap(body))

    def _make_spark_card(self, title: str, color: str):
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(3)

        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; font-weight: 700; color: #71717A;")
        lay.addWidget(t)

        val = QLabel("—")
        val.setStyleSheet(f"font-size: 17px; font-weight: 700; color: {color};")
        lay.addWidget(val)

        sub = QLabel("—")
        sub.setStyleSheet("font-size: 11px; color: #A1A1AA;")
        lay.addWidget(sub)

        chart = SparklineChart(line_color=color)
        lay.addWidget(chart)
        return val, sub, chart, card


class RamOptimizerView(QWidget):
    """Dedicated Deep RAM Optimizer: Live Breakdown, Standby Purge, Auto-RAM Guard & Per-App Trim."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # 1. Hero Memory Breakdown Card
        hero = QFrame()
        hero.setObjectName("HeroCard")
        hlay = QHBoxLayout(hero)
        hlay.setContentsMargins(22, 18, 22, 18)
        hlay.setSpacing(22)

        self.ram_gauge = CircularScoreGauge(subtitle_prefix="RAM", color_start="#8B5CF6", color_end="#38BDF8")
        hlay.addWidget(self.ram_gauge, 0, Qt.AlignmentFlag.AlignCenter)

        rcol = QVBoxLayout()
        rcol.setSpacing(8)
        self.ram_title = QLabel("Memantau Memori Sistem...")
        self.ram_title.setStyleSheet("font-size: 17px; font-weight: 700; color: #FAFAFA;")
        rcol.addWidget(self.ram_title)

        self.mem_bar = MemoryBreakdownBar()
        rcol.addWidget(self.mem_bar)

        self.ram_legend = QLabel("Active: — GB  •  Standby/Cached: — GB  •  Free: — GB  •  Commit: — / — GB")
        self.ram_legend.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        rcol.addWidget(self.ram_legend)

        self.last_freed_lbl = QLabel("Klik 'Bersihkan RAM' untuk trim aplikasi idle dan mengosongkan Standby Memory List.")
        self.last_freed_lbl.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
        rcol.addWidget(self.last_freed_lbl)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btn_deep = QPushButton(" Bersihkan RAM (Deep Clean)")
        btn_deep.setIcon(svg_icon("sparkles", "#030712", 15))
        btn_deep.setObjectName("PrimaryBtn")
        btn_deep.setFixedHeight(36)
        btn_deep.clicked.connect(self.ctrl.deep_clean_ram_async)
        btns.addWidget(btn_deep)

        btn_standby = QPushButton(" Purge Standby Cache")
        btn_standby.setIcon(svg_icon("memory", "#E4E4E7", 15))
        btn_standby.setObjectName("GhostBtn")
        btn_standby.setFixedHeight(36)
        btn_standby.clicked.connect(self.ctrl.purge_standby_only_async)
        btns.addWidget(btn_standby)
        btns.addStretch()
        rcol.addLayout(btns)

        hlay.addLayout(rcol, 1)
        lay.addWidget(hero)

        # 2. Auto-Clean RAM Guard Card
        acard = QFrame()
        acard.setObjectName("Card")
        alay = QHBoxLayout(acard)
        alay.setContentsMargins(18, 14, 18, 14)
        alay.setSpacing(14)

        ainfo = QVBoxLayout()
        ainfo.addWidget(QLabel("Auto-Clean RAM Guard (Latar Belakang)", styleSheet="font-size: 14px; font-weight: 700;"))
        ainfo.addWidget(
            QLabel(
                "Otomatis membersihkan RAM jika pemakaian melewati batas (cocok saat multitasking atau bermain game/emulator di RAM 16 GB).",
                styleSheet="color: #A1A1AA; font-size: 12px;",
            )
        )
        alay.addLayout(ainfo, 1)

        alay.addWidget(QLabel("Batas:", styleSheet="color: #A1A1AA; font-size: 12px;"))
        self.threshold_combo = QComboBox()
        for pct in (70, 75, 80, 85):
            self.threshold_combo.addItem(f"{pct}% RAM", pct)
        cur_thresh = int(self.ctrl.settings.get("auto_ram_clean_threshold", 80))
        idx = self.threshold_combo.findData(cur_thresh)
        self.threshold_combo.setCurrentIndex(max(0, idx))
        self.threshold_combo.currentIndexChanged.connect(
            lambda: self.ctrl.update_setting("auto_ram_clean_threshold", self.threshold_combo.currentData())
        )
        alay.addWidget(self.threshold_combo)

        self.auto_ram_switch = ToggleSwitch(checked=bool(self.ctrl.settings.get("auto_ram_clean_enabled", False)))
        self.auto_ram_switch.toggled.connect(lambda v: self.ctrl.update_setting("auto_ram_clean_enabled", v))
        alay.addWidget(self.auto_ram_switch)
        lay.addWidget(acard)

        # 3. Top RAM-Hogging Apps Table (Trim or End Task)
        tcard = QFrame()
        tcard.setObjectName("Card")
        tlay = QVBoxLayout(tcard)
        tlay.setContentsMargins(18, 16, 18, 16)
        tlay.setSpacing(10)

        thdr = QHBoxLayout()
        thdr.addWidget(QLabel("Aplikasi Pemakan RAM Terbesar (Trim Tanpa Menutup Aplikasi)", styleSheet="font-size: 14px; font-weight: 700;"))
        thdr.addStretch()
        btn_ref = QPushButton(" Refresh")
        btn_ref.setIcon(svg_icon("refresh", "#E4E4E7", 14))
        btn_ref.setObjectName("GhostBtn")
        btn_ref.clicked.connect(self.refresh_ram_view)
        thdr.addWidget(btn_ref)
        tlay.addLayout(thdr)

        self.ram_table = QTableWidget(0, 5)
        self.ram_table.setHorizontalHeaderLabels(["PID", "Process", "RAM (MB)", "CPU %", "Aksi"])
        self.ram_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ram_table.setColumnWidth(4, 175)
        self.ram_table.setAlternatingRowColors(True)
        self.ram_table.setMinimumHeight(310)
        tlay.addWidget(self.ram_table)
        lay.addWidget(tcard, 1)

        outer.addWidget(_scroll_wrap(body))

    def refresh_ram_view(self) -> None:
        from optimasi.core.ram_optimizer import get_memory_details
        from optimasi.core.system_info import get_top_processes

        mem = get_memory_details()
        self.ram_gauge.set_score(mem["percent"], "USED", "%")
        self.ram_title.setText(
            f"RAM Terpakai: {mem['used_gb']} GB / {mem['total_gb']} GB  ({mem['available_gb']} GB Tersedia)"
        )
        self.mem_bar.set_ratios(mem["used_gb"], mem["cached_gb"], mem["total_gb"])
        self.ram_legend.setText(
            f"<span style='color:#38BDF8;'>●</span> Active: <b>{mem['used_gb']} GB</b>  •  "
            f"<span style='color:#8B5CF6;'>●</span> Standby/Cache: <b>{mem['cached_gb']} GB</b>  •  "
            f"<span style='color:#71717A;'>●</span> Free: <b>{mem['free_gb']} GB</b>  •  "
            f"Commit: {mem['commit_used_gb']} / {mem['commit_total_gb']} GB"
        )

        rows = get_top_processes(18)
        self.ram_table.setRowCount(len(rows))
        for r, proc in enumerate(rows):
            self.ram_table.setRowHeight(r, 38)
            self.ram_table.setItem(r, 0, QTableWidgetItem(str(proc["pid"])))
            self.ram_table.setItem(r, 1, QTableWidgetItem(proc["name"]))
            self.ram_table.setItem(r, 2, QTableWidgetItem(f"{proc['ram_mb']:.1f}"))
            self.ram_table.setItem(r, 3, QTableWidgetItem(f"{proc['cpu_percent']:.1f}%"))

            cell = QWidget()
            clay = QHBoxLayout(cell)
            clay.setContentsMargins(4, 2, 4, 2)
            clay.setSpacing(6)

            btn_trim = QPushButton("Trim")
            btn_trim.setObjectName("GhostBtn")
            btn_trim.clicked.connect(lambda _=False, pid=proc["pid"]: self.ctrl.trim_process_ram(pid, on_done=self.refresh_ram_view))
            clay.addWidget(btn_trim)

            btn_kill = QPushButton("Protected" if proc["protected"] else "End")
            btn_kill.setObjectName("GhostBtn" if proc["protected"] else "DangerBtn")
            btn_kill.setEnabled(not proc["protected"])
            btn_kill.clicked.connect(lambda _=False, pid=proc["pid"]: self.ctrl.kill_process(pid, on_done=self.refresh_ram_view))
            clay.addWidget(btn_kill)
            self.ram_table.setCellWidget(r, 4, cell)


class BoosterView(QWidget):
    """1-Click Game & Emulator Booster, Laptop Thermal AC/DC Control, and Process Monitor."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        bcard = QFrame()
        bcard.setObjectName("HeroCard")
        blay = QHBoxLayout(bcard)
        blay.setContentsMargins(20, 18, 20, 18)

        binfo = QVBoxLayout()
        self.boost_title = QLabel("Game & Emulator Booster: STANDBY")
        self.boost_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FAFAFA;")
        binfo.addWidget(self.boost_title)
        bdesc = QLabel(
            "Mengaktifkan High Performance Power Plan sementara, membersihkan RAM Working Sets, "
            "dan flush DNS sebelum membuka Game atau Emulator (MuMuPlayer / BlueStacks). Bisa di-restore 1 klik."
        )
        bdesc.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        bdesc.setWordWrap(True)
        binfo.addWidget(bdesc)
        blay.addLayout(binfo, 1)

        self.btn_activate_boost = QPushButton(" Boost Sekarang")
        self.btn_activate_boost.setIcon(svg_icon("zap", "#030712", 15))
        self.btn_activate_boost.setObjectName("PrimaryBtn")
        self.btn_activate_boost.setFixedHeight(38)
        self.btn_activate_boost.clicked.connect(self.ctrl.toggle_game_boost)
        blay.addWidget(self.btn_activate_boost)

        self.btn_restore_boost = QPushButton("Restore Plan")
        self.btn_restore_boost.setObjectName("GhostBtn")
        self.btn_restore_boost.setFixedHeight(38)
        self.btn_restore_boost.clicked.connect(self.ctrl.restore_game_boost)
        blay.addWidget(self.btn_restore_boost)
        lay.addWidget(bcard)

        tcard = QFrame()
        tcard.setObjectName("Card")
        tlay = QVBoxLayout(tcard)
        tlay.setContentsMargins(18, 16, 18, 16)
        tlay.setSpacing(8)
        tlay.addWidget(QLabel("Laptop Thermal & CPU Boost Controller (AC Charger vs Battery DC)", styleSheet="font-size: 14px; font-weight: 700;"))
        tlay.addWidget(QLabel("Atur batas CPU boost laptop agar tetap adem saat kerja ringan atau maksimal saat gaming.", styleSheet="color: #A1A1AA; font-size: 12px;"))

        tbtns = QHBoxLayout()
        for mode, label, obj in [
            ("cool_quiet", "Cool & Quiet (99% AC / 80% DC)", "SuccessBtn"),
            ("balanced_laptop", "Balanced Laptop (100% AC / 85% DC)", "GhostBtn"),
            ("max_turbo", "Max Turbo (100% AC / 100% DC)", "WarningBtn"),
        ]:
            b = QPushButton(label)
            b.setObjectName(obj)
            b.clicked.connect(lambda _=False, m=mode: self.ctrl.apply_thermal_mode(m))
            tbtns.addWidget(b)
        tlay.addLayout(tbtns)
        lay.addWidget(tcard)

        pcard = QFrame()
        pcard.setObjectName("Card")
        play = QVBoxLayout(pcard)
        play.setContentsMargins(18, 16, 18, 16)
        play.setSpacing(8)

        phdr = QHBoxLayout()
        phdr.addWidget(QLabel("Live Top Processes Monitor", styleSheet="font-size: 14px; font-weight: 700;"))
        phdr.addStretch()
        btn_ref = QPushButton(" Refresh")
        btn_ref.setIcon(svg_icon("refresh", "#E4E4E7", 14))
        btn_ref.setObjectName("GhostBtn")
        btn_ref.clicked.connect(self.refresh_processes)
        phdr.addWidget(btn_ref)
        play.addLayout(phdr)

        self.proc_table = QTableWidget(0, 5)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "RAM (MB)", "CPU %", "Action"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.proc_table.setAlternatingRowColors(True)
        self.proc_table.setMinimumHeight(290)
        play.addWidget(self.proc_table)
        lay.addWidget(pcard, 1)

        outer.addWidget(_scroll_wrap(body))

    def refresh_processes(self) -> None:
        from optimasi.core.system_info import get_top_processes

        rows = get_top_processes(18)
        self.proc_table.setRowCount(len(rows))
        for r, proc in enumerate(rows):
            self.proc_table.setRowHeight(r, 36)
            self.proc_table.setItem(r, 0, QTableWidgetItem(str(proc["pid"])))
            self.proc_table.setItem(r, 1, QTableWidgetItem(proc["name"]))
            self.proc_table.setItem(r, 2, QTableWidgetItem(f"{proc['ram_mb']:.1f}"))
            self.proc_table.setItem(r, 3, QTableWidgetItem(f"{proc['cpu_percent']:.1f}%"))

            btn = QPushButton("Protected" if proc["protected"] else "End Task")
            btn.setObjectName("GhostBtn" if proc["protected"] else "DangerBtn")
            btn.setEnabled(not proc["protected"])
            btn.clicked.connect(lambda _=False, pid=proc["pid"]: self.ctrl.kill_process(pid, on_done=self.refresh_processes))
            self.proc_table.setCellWidget(r, 4, btn)


class CategoryView(QWidget):
    """Dynamic Tweak Category / Search View with Network, AppX, and Startup tools."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        self.current_tweaks: list[Tweak] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(12)

        bar = QHBoxLayout()
        self.header_lbl = QLabel("Tweaks")
        self.header_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        bar.addWidget(self.header_lbl, 1)

        for txt, obj, fn in [
            ("Select Safe", "GhostBtn", lambda: self._select(safe_only=True)),
            ("Select All", "GhostBtn", lambda: self._select(value=True)),
            ("Clear", "GhostBtn", lambda: self._select(value=False)),
            ("Apply Selected", "PrimaryBtn", lambda: self.ctrl.run_tweaks_batch(self.current_tweaks, revert=False)),
            ("Revert Selected", "WarningBtn", lambda: self.ctrl.run_tweaks_batch(self.current_tweaks, revert=True)),
        ]:
            b = QPushButton(txt)
            b.setObjectName(obj)
            b.clicked.connect(fn)
            bar.addWidget(b)
        lay.addLayout(bar)

        self.inner = QWidget()
        self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setContentsMargins(0, 4, 4, 12)
        self.inner_lay.setSpacing(10)
        lay.addWidget(_scroll_wrap(self.inner), 1)

    def _clear_inner(self) -> None:
        while self.inner_lay.count():
            item = self.inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _select(self, value: bool = True, safe_only: bool = False) -> None:
        for t in self.current_tweaks:
            state = (t.risk.value == "SAFE") if safe_only else value
            self.ctrl.tweak_checked[t.id] = state
        for i in range(self.inner_lay.count()):
            w = self.inner_lay.itemAt(i).widget()
            if isinstance(w, TweakCardWidget):
                w.switch.setChecked(self.ctrl.tweak_checked.get(w.tweak.id, False))

    def load_tweaks(self, title: str, tweaks: list[Tweak], mode: str = "") -> None:
        self._clear_inner()
        self.current_tweaks = list(tweaks)
        self.header_lbl.setText(f"{title} ({len(tweaks)})")

        if mode == "Network & DNS":
            self._add_network_panel()
        elif mode == "Privacy & Debloat":
            self._add_appx_panel()
        elif mode == "Services & System":
            self._add_startup_panel()

        for tweak in tweaks:
            card = TweakCardWidget(
                tweak=tweak,
                checked=self.ctrl.tweak_checked.get(tweak.id, False),
                on_toggle=lambda tid, val: self.ctrl.tweak_checked.__setitem__(tid, val),
                on_apply=lambda tw: self.ctrl.run_single_tweak(tw, revert=False),
                on_revert=lambda tw: self.ctrl.run_single_tweak(tw, revert=True),
            )
            self.inner_lay.addWidget(card)
        self.inner_lay.addStretch()

    def _add_network_panel(self) -> None:
        panel = QFrame()
        panel.setObjectName("Card")
        play = QVBoxLayout(panel)
        play.setContentsMargins(16, 14, 16, 14)
        play.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Quick DNS Switcher & Multi-Region Ping Benchmark", styleSheet="font-weight: 700; font-size: 13px;"))
        hdr.addStretch()
        btn_ping = QPushButton("Run Ping Benchmark")
        btn_ping.setObjectName("PrimaryBtn")
        btn_ping.clicked.connect(lambda: self.ctrl.run_ping_benchmark(self._render_ping_results))
        hdr.addWidget(btn_ping)
        play.addLayout(hdr)

        dns_row = QHBoxLayout()
        for key, label, primary, secondary in DNS_PRESETS:
            short = label.split("(")[0].strip().replace(" Public", "").replace(" Security", "").replace(" Ad-Blocking", "")
            b = QPushButton(f"{short}" + (f" ({primary})" if primary else ""))
            b.setObjectName("GhostBtn")
            b.clicked.connect(lambda _=False, p=primary, s=secondary, lbl=label: self.ctrl.apply_quick_dns(p, s, lbl))
            dns_row.addWidget(b)
        play.addLayout(dns_row)

        self.ping_row = QHBoxLayout()
        self.ping_row.addWidget(QLabel("Klik 'Run Ping Benchmark' untuk melihat latensi DNS & server gaming Asia (SG/Tokyo).", styleSheet="color: #A1A1AA; font-size: 11px;"))
        play.addLayout(self.ping_row)
        self.inner_lay.addWidget(panel)

    def _render_ping_results(self, rows: list[dict[str, str]]) -> None:
        while self.ping_row.count():
            item = self.ping_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for row in rows:
            box = QFrame()
            box.setStyleSheet("background-color: #0D0D12; border: 1px solid #22222C; border-radius: 8px; padding: 4px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(8, 6, 8, 6)
            bl.addWidget(QLabel(row["label"], styleSheet="font-size: 10px; color: #A1A1AA; font-weight: 600;"))
            bl.addWidget(QLabel(row["latency"], styleSheet="font-size: 13px; color: #38BDF8; font-weight: 700;"))
            self.ping_row.addWidget(box, 1)

    def _add_appx_panel(self) -> None:
        panel = QFrame()
        panel.setObjectName("Card")
        play = QVBoxLayout(panel)
        play.setContentsMargins(16, 14, 16, 14)
        play.setSpacing(10)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Selective UWP Bloatware Remover (Store & Terminal Aman)", styleSheet="font-weight: 700; font-size: 13px;"))
        hdr.addStretch()
        btn_scan = QPushButton("Detect Installed")
        btn_scan.setObjectName("GhostBtn")
        btn_scan.clicked.connect(lambda: self.ctrl.detect_installed_appx(self._mark_installed_appx))
        hdr.addWidget(btn_scan)

        btn_rem = QPushButton("Remove Checked Apps")
        btn_rem.setObjectName("DangerBtn")
        btn_rem.clicked.connect(self.ctrl.remove_checked_appx)
        hdr.addWidget(btn_rem)
        play.addLayout(hdr)

        grid = QGridLayout()
        self.appx_checks: dict[str, QCheckBox] = {}
        for idx, (pkg, friendly) in enumerate(SAFE_BLOAT_APPX):
            cb = QCheckBox(friendly)
            cb.setChecked(self.ctrl.appx_checked.get(pkg, True))
            cb.toggled.connect(lambda state, p=pkg: self.ctrl.appx_checked.__setitem__(p, state))
            self.appx_checks[pkg] = cb
            grid.addWidget(cb, idx // 4, idx % 4)
        play.addLayout(grid)
        self.inner_lay.addWidget(panel)

    def _mark_installed_appx(self, installed: set[str]) -> None:
        for pkg, friendly in SAFE_BLOAT_APPX:
            cb = self.appx_checks.get(pkg)
            if not cb:
                continue
            if pkg in installed:
                cb.setText(f"{friendly} [Installed]")
                cb.setChecked(True)
            else:
                cb.setText(f"{friendly} [Not Found]")
                cb.setChecked(False)

    def _add_startup_panel(self) -> None:
        from optimasi.tweaks.startup import list_startup_items

        panel = QFrame()
        panel.setObjectName("Card")
        play = QVBoxLayout(panel)
        play.setContentsMargins(16, 14, 16, 14)
        play.setSpacing(8)
        play.addWidget(QLabel("Windows Startup Programs (HKCU & HKLM Run)", styleSheet="font-weight: 700; font-size: 13px;"))

        items = list_startup_items()
        if not items:
            play.addWidget(QLabel("No startup entries detected.", styleSheet="color: #71717A;"))
        else:
            for item in items:
                row = QHBoxLayout()
                badge = QLabel(item.hive)
                badge.setStyleSheet("background-color: #1A1A26; color: #38BDF8; padding: 2px 7px; border-radius: 5px; font-size: 10px; font-weight: 700;")
                row.addWidget(badge)
                lbl = QLabel(f"<b>{item.name}</b> <span style='color:#71717A;'>({item.command[:65]})</span>")
                row.addWidget(lbl, 1)
                sw = ToggleSwitch(checked=item.enabled)
                sw.toggled.connect(lambda state, it=item: self.ctrl.toggle_startup(it.hive, it.name, state))
                row.addWidget(sw)
                play.addLayout(row)
        self.inner_lay.addWidget(panel)


class CleanerView(QWidget):
    """Junk & Shader Cache Cleaner + DISM/SFC/TRIM Repair Tools."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        hdr = QHBoxLayout()
        self.scan_lbl = QLabel("Junk, Cache & Shader Cleaner")
        self.scan_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        hdr.addWidget(self.scan_lbl, 1)

        for txt, ico, obj, fn in [
            (" Scan Junk", "search", "GhostBtn", self.refresh_scan),
            (" Clean Selected", "trash", "PrimaryBtn", self.clean_selected),
            (" Bersihkan RAM", "memory", "SuccessBtn", self.ctrl.deep_clean_ram_async),
        ]:
            b = QPushButton(txt)
            b.setIcon(svg_icon(ico, "#030712" if obj == "PrimaryBtn" else "#E4E4E7", 14))
            b.setObjectName(obj)
            b.clicked.connect(fn)
            hdr.addWidget(b)
        lay.addLayout(hdr)

        self.junk_container = QVBoxLayout()
        self.junk_container.setSpacing(8)
        lay.addLayout(self.junk_container)

        self.recycle_cb = QCheckBox("Kosongkan juga Windows Recycle Bin")
        lay.addWidget(self.recycle_cb)

        lay.addWidget(QLabel("Windows System Repair & SSD Maintenance", styleSheet="font-size: 15px; font-weight: 700; margin-top: 8px;"))

        rgrid = QGridLayout()
        rgrid.setSpacing(12)
        repairs = [
            ("dism_restore", "DISM RestoreHealth", "Memperbaiki image Windows yang corrupt."),
            ("sfc", "SFC /scannow", "Memindai dan memulihkan file sistem Windows."),
            ("dism_cleanup", "DISM Component Cleanup", "Membersihkan backup komponen WinSxS lama."),
            ("ssd_trim", "SSD ReTrim (Drive C:)", "Menjaga kecepatan tulis NVMe/SATA SSD tetap optimal."),
            ("flush_dns", "Flush DNS Cache", "Menghapus cache DNS resolver yang usang."),
            ("network_reset", "Winsock & TCP/IP Reset", "Mereset socket jaringan dan konfigurasi IP."),
        ]
        for idx, (mode, title, desc) in enumerate(repairs):
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 14, 16, 14)
            cl.addWidget(QLabel(title, styleSheet="font-weight: 700; font-size: 13px;"))
            dl = QLabel(desc)
            dl.setStyleSheet("color: #A1A1AA; font-size: 11px;")
            dl.setWordWrap(True)
            cl.addWidget(dl)
            b = QPushButton("Run Tool")
            b.setObjectName("GhostBtn")
            b.clicked.connect(lambda _=False, m=mode, t=title: self.ctrl.run_repair(m, t))
            cl.addWidget(b)
            rgrid.addWidget(card, idx // 3, idx % 3)

        lay.addLayout(rgrid)
        lay.addStretch()
        outer.addWidget(_scroll_wrap(body))

        self.junk_checks: dict[str, QCheckBox] = {}
        self.junk_checked_state: dict[str, bool] = {}
        self._scanned_once = False

    def refresh_scan(self) -> None:
        self._scanned_once = True
        self.ctrl.scan_junk_async(self._render_junk_rows)

    def _render_junk_rows(self, stats) -> None:
        for key, cb in list(self.junk_checks.items()):
            try:
                self.junk_checked_state[key] = cb.isChecked()
            except RuntimeError:
                pass
        self.junk_checks.clear()

        while self.junk_container.count():
            item = self.junk_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total_mb = round(sum(s.size_mb for s in stats), 2)
        self.scan_lbl.setText(f"Junk, Cache & Shader Cleaner (~{total_mb} MB Reclaimable)")
        for s in stats:
            row_card = QFrame()
            row_card.setObjectName("Card")
            rl = QHBoxLayout(row_card)
            rl.setContentsMargins(14, 10, 16, 10)

            default_on = s.key in ("user_temp", "windows_temp", "shader_cache", "crash_wer")
            checked = self.junk_checked_state.get(s.key, default_on)
            self.junk_checked_state[s.key] = checked
            cb = QCheckBox(f"{s.label} — {s.description}")
            cb.setChecked(checked)
            cb.toggled.connect(lambda val, k=s.key: self.junk_checked_state.__setitem__(k, val))
            self.junk_checks[s.key] = cb
            rl.addWidget(cb, 1)

            size_lbl = QLabel(f"{s.file_count} files • {s.size_mb} MB")
            size_lbl.setStyleSheet(f"font-family: Consolas; font-weight: 700; color: {'#38BDF8' if s.size_mb > 0 else '#71717A'};")
            rl.addWidget(size_lbl)
            self.junk_container.addWidget(row_card)

    def clean_selected(self) -> None:
        keys = [k for k, checked in self.junk_checked_state.items() if checked]
        self.ctrl.clean_junk_async(keys, self.recycle_cb.isChecked(), on_done=self.refresh_scan)


class BackupUpdatesView(QWidget):
    """In-App GitHub Auto-Updater settings + System Backup & Visual Undo Timeline."""

    def __init__(self, app_ctrl):
        super().__init__()
        self.ctrl = app_ctrl
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        ucard = QFrame()
        ucard.setObjectName("HeroCard")
        ulay = QVBoxLayout(ucard)
        ulay.setContentsMargins(20, 18, 20, 18)
        ulay.setSpacing(10)

        uhdr = QHBoxLayout()
        uhdr.addWidget(QLabel(f"In-App Auto-Updater (Current: v{APP_VERSION})", styleSheet="font-size: 15px; font-weight: 700; color: #38BDF8;"))
        uhdr.addStretch()
        btn_chk = QPushButton(" Cek Update Sekarang")
        btn_chk.setIcon(svg_icon("download", "#030712", 14))
        btn_chk.setObjectName("PrimaryBtn")
        btn_chk.clicked.connect(lambda: self.ctrl.check_updates_async(manual=True))
        uhdr.addWidget(btn_chk)
        ulay.addLayout(uhdr)

        self.update_status_lbl = QLabel("Mengambil info rilis langsung dari GitHub tanpa perlu download manual dari browser.")
        self.update_status_lbl.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        ulay.addWidget(self.update_status_lbl)

        opts = QHBoxLayout()
        self.auto_check_cb = QCheckBox("Otomatis cek update setiap kali aplikasi dibuka")
        self.auto_check_cb.setChecked(self.ctrl.settings.get("auto_check_updates", True))
        self.auto_check_cb.toggled.connect(lambda v: self.ctrl.update_setting("auto_check_updates", v))
        opts.addWidget(self.auto_check_cb)

        self.tray_cb = QCheckBox("Minimize ke System Tray saat tombol close (X) ditekan")
        self.tray_cb.setChecked(self.ctrl.settings.get("minimize_to_tray", True))
        self.tray_cb.toggled.connect(lambda v: self.ctrl.update_setting("minimize_to_tray", v))
        opts.addWidget(self.tray_cb)
        opts.addStretch()
        ulay.addLayout(opts)
        lay.addWidget(ucard)

        bcard = QFrame()
        bcard.setObjectName("Card")
        blay = QHBoxLayout(bcard)
        blay.setContentsMargins(18, 16, 18, 16)
        blay.addWidget(QLabel("Windows Backup & Restore Point", styleSheet="font-size: 14px; font-weight: 700;"), 1)
        b1 = QPushButton("Create Restore Point")
        b1.setObjectName("PrimaryBtn")
        b1.clicked.connect(self.ctrl.action_restore_point)
        blay.addWidget(b1)
        b2 = QPushButton("Export Registry Backup")
        b2.setObjectName("GhostBtn")
        b2.clicked.connect(self.ctrl.action_backup_registry)
        blay.addWidget(b2)
        lay.addWidget(bcard)

        shdr = QHBoxLayout()
        shdr.addWidget(QLabel("Visual Undo Sessions Timeline", styleSheet="font-size: 15px; font-weight: 700;"), 1)
        bref = QPushButton("Refresh Timeline")
        bref.setObjectName("GhostBtn")
        bref.clicked.connect(self.refresh_sessions)
        shdr.addWidget(bref)
        lay.addLayout(shdr)

        self.sessions_box = QVBoxLayout()
        self.sessions_box.setSpacing(8)
        lay.addLayout(self.sessions_box)
        lay.addStretch()

        outer.addWidget(_scroll_wrap(body))
        self.refresh_sessions()

    def refresh_sessions(self) -> None:
        from optimasi.core.backup import list_undo_sessions

        while self.sessions_box.count():
            item = self.sessions_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = list_undo_sessions()
        if not sessions:
            self.sessions_box.addWidget(QLabel("Belum ada riwayat session undo. Jalankan tweak dulu untuk merekam snapshot.", styleSheet="color: #71717A;"))
            return

        for s in sessions[:15]:
            card = QFrame()
            card.setObjectName("Card")
            rl = QHBoxLayout(card)
            rl.setContentsMargins(16, 12, 16, 12)
            rl.addWidget(QLabel(f"<b>{s['label']}</b> — <span style='color:#A1A1AA;'>{s['timestamp']} ({s['entry_count']} changes)</span>"), 1)
            rev_btn = QPushButton("Revert Session")
            rev_btn.setObjectName("WarningBtn")
            rev_btn.clicked.connect(lambda _=False, sp=s["path"]: self.ctrl.revert_session_path(sp, on_done=self.refresh_sessions))
            rl.addWidget(rev_btn)
            self.sessions_box.addWidget(card)
