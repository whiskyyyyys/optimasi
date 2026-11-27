"""Custom PySide6 widgets: CircularScoreGauge, MemoryBreakdownBar, SparklineChart, ToggleSwitch, ToastNotification, UpdateBanner/Dialog, TweakCard."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from optimasi.core.updater import UpdateInfo, download_update, launch_update_installer
from optimasi.tweaks.models import Tweak


class ToggleSwitch(QAbstractButton):
    """Sleek animated pill toggle switch."""

    def __init__(self, checked: bool = False, accent: str = "#0EA5E9", parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accent = QColor(accent)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, val: float) -> None:
        self._pos = val
        self.update()

    thumbPos = Property(float, _get_pos, _set_pos)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._pos = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        track_color = self._accent if self.isChecked() else QColor("#272735")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, r.width(), r.height()), 11, 11)

        knob_d = 16
        x = 3 + self._pos * (r.width() - knob_d - 6)
        p.setBrush(QColor("#FAFAFA"))
        p.drawEllipse(QRectF(x, 3, knob_d, knob_d))


class CircularScoreGauge(QWidget):
    """Animated circular donut gauge (0-100) for Health Score or RAM Usage."""

    def __init__(self, subtitle_prefix: str = "GRADE", color_start: str = "#38BDF8", color_end: str = "#10B981", parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(136, 136)
        self._score = 0.0
        self._subtitle = f"{subtitle_prefix} —"
        self._prefix = subtitle_prefix
        self._c1 = QColor(color_start)
        self._c2 = QColor(color_end)
        self._suffix = ""
        self._anim = QPropertyAnimation(self, b"scoreValue", self)
        self._anim.setDuration(550)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_score(self) -> float:
        return self._score

    def _set_score(self, val: float) -> None:
        self._score = val
        self.update()

    scoreValue = Property(float, _get_score, _set_score)

    def set_score(self, score: int | float, badge_text: str, suffix: str = "") -> None:
        self._subtitle = f"{self._prefix} {badge_text}".strip() if self._prefix else badge_text
        self._suffix = suffix
        self._anim.stop()
        self._anim.setStartValue(self._score)
        self._anim.setEndValue(float(max(0.0, min(100.0, score))))
        self._anim.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 12
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)

        bg_pen = QPen(QColor("#1F1F2C"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, self._c1)
        grad.setColorAt(1.0, self._c2)
        fg_pen = QPen(grad, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(fg_pen)
        span = -int((self._score / 100.0) * 360 * 16)
        p.drawArc(rect, 90 * 16, span)

        p.setPen(QColor("#FAFAFA"))
        p.setFont(QFont("Segoe UI", 21, QFont.Weight.Bold))
        p.drawText(QRectF(0, 28, self.width(), 44), Qt.AlignmentFlag.AlignCenter, f"{int(round(self._score))}{self._suffix}")

        p.setPen(self._c1)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.drawText(QRectF(0, 74, self.width(), 22), Qt.AlignmentFlag.AlignCenter, self._subtitle)


class MemoryBreakdownBar(QWidget):
    """Segmented rounded bar visualizing Active, Standby/Cached, and Free RAM."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self._active_ratio = 0.4
        self._cached_ratio = 0.25

    def set_ratios(self, active_gb: float, cached_gb: float, total_gb: float) -> None:
        tot = max(0.1, total_gb)
        self._active_ratio = max(0.0, min(1.0, active_gb / tot))
        self._cached_ratio = max(0.0, min(1.0 - self._active_ratio, cached_gb / tot))
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = 12.0
        y = 4.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#1E1E2B"))
        p.drawRoundedRect(QRectF(0, y, w, h), 6, 6)

        act_w = w * self._active_ratio
        cac_w = w * self._cached_ratio
        if cac_w > 1:
            p.setBrush(QColor("#8B5CF6"))
            p.drawRoundedRect(QRectF(0, y, act_w + cac_w, h), 6, 6)
        if act_w > 1:
            p.setBrush(QColor("#38BDF8"))
            p.drawRoundedRect(QRectF(0, y, act_w, h), 6, 6)


class SparklineChart(QWidget):
    """Real-time rolling sparkline area chart for CPU / RAM / Network."""

    def __init__(self, line_color: str = "#38BDF8", max_points: int = 36, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.setMaximumHeight(60)
        self._color = QColor(line_color)
        self._max_points = max_points
        self._values: list[float] = [0.0] * 12

    def push_value(self, value: float, ceiling: float = 100.0) -> None:
        norm = max(0.0, min(1.0, value / max(1.0, ceiling)))
        self._values.append(norm)
        if len(self._values) > self._max_points:
            self._values = self._values[-self._max_points :]
        self.update()

    def paintEvent(self, _event) -> None:
        if len(self._values) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())

        # Subtle baseline guide
        p.setPen(QPen(QColor("#1F1F2B"), 1, Qt.PenStyle.DashLine))
        p.drawLine(0, int(h * 0.5), int(w), int(h * 0.5))

        pad_y = 6.0
        usable_h = max(8.0, h - 2 * pad_y)
        step = w / max(1, len(self._values) - 1)

        line_path = QPainterPath()
        fill_path = QPainterPath()
        for i, val in enumerate(self._values):
            x = i * step
            y = pad_y + usable_h * (1.0 - val)
            if i == 0:
                line_path.moveTo(x, y)
                fill_path.moveTo(x, h)
                fill_path.lineTo(x, y)
            else:
                line_path.lineTo(x, y)
                fill_path.lineTo(x, y)
        fill_path.lineTo(w, h)
        fill_path.closeSubpath()

        fill_grad = QLinearGradient(0, 0, 0, h)
        c_top = QColor(self._color)
        c_top.setAlpha(85)
        c_bot = QColor(self._color)
        c_bot.setAlpha(4)
        fill_grad.setColorAt(0.0, c_top)
        fill_grad.setColorAt(1.0, c_bot)
        p.fillPath(fill_path, fill_grad)

        p.setPen(QPen(self._color, 2.0))
        p.drawPath(line_path)


class ToastNotification(QFrame):
    """Floating bottom-right toast pill inside MainWindow."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("ToastFrame")
        self.setVisible(False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color: #38BDF8; font-size: 12px;")
        lay.addWidget(self.dot)
        self.lbl = QLabel("")
        self.lbl.setStyleSheet("color: #FAFAFA; font-size: 12px; font-weight: 600;")
        lay.addWidget(self.lbl)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_toast(self, message: str, kind: str = "info", duration_ms: int = 3600) -> None:
        colors = {"success": "#34D399", "warning": "#FBBF24", "error": "#F87171", "info": "#38BDF8"}
        c = colors.get(kind, "#38BDF8")
        self.dot.setStyleSheet(f"color: {c}; font-size: 12px;")
        self.setStyleSheet(f"QFrame#ToastFrame {{ background-color: #181824; border: 1px solid {c}; border-radius: 10px; }}")
        self.lbl.setText(message)
        self.adjustSize()
        self.reposition()
        self.raise_()
        self.setVisible(True)
        self._timer.start(duration_ms)

    def reposition(self) -> None:
        p = self.parentWidget()
        if p:
            self.move(max(16, p.width() - self.width() - 24), max(16, p.height() - self.height() - 50))


class UpdateBanner(QFrame):
    """In-app notification banner shown when a newer GitHub Release exists."""

    update_clicked = Signal()
    details_clicked = Signal()
    dismiss_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("UpdateBanner")
        self.setVisible(False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)

        self.label = QLabel("Update tersedia!")
        self.label.setStyleSheet("font-weight: 700; color: #E0F2FE; font-size: 13px;")
        lay.addWidget(self.label, 1)

        btn_details = QPushButton("Lihat Changelog")
        btn_details.setObjectName("GhostBtn")
        btn_details.clicked.connect(self.details_clicked.emit)
        lay.addWidget(btn_details)

        btn_update = QPushButton("Update Sekarang")
        btn_update.setObjectName("PrimaryBtn")
        btn_update.clicked.connect(self.update_clicked.emit)
        lay.addWidget(btn_update)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("GhostBtn")
        btn_close.setFixedWidth(32)
        btn_close.clicked.connect(self._on_dismiss)
        lay.addWidget(btn_close)

    def _on_dismiss(self) -> None:
        self.setVisible(False)
        self.dismiss_clicked.emit()

    def show_update(self, info: UpdateInfo) -> None:
        size_mb = round(info.asset_size / (1024 * 1024), 1) if info.asset_size else 0
        size_txt = f" ({size_mb} MB)" if size_mb else ""
        self.label.setText(
            f"Update Baru Tersedia: v{info.latest_version}{size_txt} — {info.release_name}"
        )
        self.setVisible(True)


class _UpdateDownloadWorker(QThread):
    progress = Signal(int, int, float)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, update: UpdateInfo):
        super().__init__()
        self.update_info = update
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            path = download_update(
                self.update_info,
                progress_cb=lambda d, t, s: self.progress.emit(d, t, s),
                cancel_check=lambda: self._cancelled,
            )
            self.finished_ok.emit(str(path))
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateDialog(QDialog):
    """Modal dialog with changelog, download progress, and silent installer launch."""

    def __init__(self, update: UpdateInfo, dry_run: bool = False, on_install_started: Callable[[], None] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.update_info = update
        self.dry_run = dry_run
        self.on_install_started = on_install_started
        self.worker: _UpdateDownloadWorker | None = None

        self.setWindowTitle(f"Update Optimasi Windows -> v{update.latest_version}")
        self.resize(560, 420)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        title = QLabel(f"Versi Baru Tersedia: v{update.latest_version}")
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #38BDF8;")
        lay.addWidget(title)

        sub = QLabel(f"Versi saat ini: v{update.current_version}  •  Paket: {update.asset_name}")
        sub.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        lay.addWidget(sub)

        notes = QTextBrowser()
        notes.setStyleSheet("background-color: #111118; border: 1px solid #22222C; border-radius: 10px; padding: 10px; color: #E4E4E7;")
        notes.setMarkdown(update.changelog)
        lay.addWidget(notes, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #A1A1AA; font-size: 11px;")
        lay.addWidget(self.status_lbl)

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_cancel = QPushButton("Nanti")
        self.btn_cancel.setObjectName("GhostBtn")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btns.addWidget(self.btn_cancel)

        self.btn_install = QPushButton("Download & Install Otomatis")
        self.btn_install.setObjectName("PrimaryBtn")
        self.btn_install.clicked.connect(self.start_download)
        btns.addWidget(self.btn_install)
        lay.addLayout(btns)

    def _on_cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
        self.reject()

    def start_download(self) -> None:
        self.btn_install.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_lbl.setText("Menghubungi GitHub Releases...")
        self.worker = _UpdateDownloadWorker(self.update_info)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_downloaded)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, downloaded: int, total: int, speed_kbps: float) -> None:
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            self.status_lbl.setText(
                f"Mengunduh: {downloaded / (1024*1024):.1f} / {total / (1024*1024):.1f} MB ({speed_kbps:.0f} KB/s)"
            )
        else:
            self.status_lbl.setText(f"Mengunduh: {downloaded / (1024*1024):.1f} MB ({speed_kbps:.0f} KB/s)")

    def _on_downloaded(self, file_path: str) -> None:
        from pathlib import Path

        self.progress_bar.setValue(100)
        self.status_lbl.setText("Menjalankan silent installer & restart aplikasi...")
        ok, msg = launch_update_installer(Path(file_path), self.update_info.is_installer, dry_run=self.dry_run)
        if not ok:
            self.status_lbl.setText(msg)
            self.btn_install.setEnabled(True)
            return
        if self.dry_run:
            self.status_lbl.setText(msg)
            self.btn_install.setEnabled(True)
            return
        self.accept()
        if self.on_install_started:
            self.on_install_started()

    def _on_failed(self, err: str) -> None:
        self.status_lbl.setText(f"Gagal mengunduh update: {err}")
        self.btn_install.setEnabled(True)


class TweakCardWidget(QFrame):
    """Sleek Obsidian card representing an individual Windows tweak."""

    def __init__(
        self,
        tweak: Tweak,
        checked: bool,
        on_toggle: Callable[[str, bool], None],
        on_apply: Callable[[Tweak], None],
        on_revert: Callable[[Tweak], None],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.tweak = tweak

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(14)

        self.switch = ToggleSwitch(checked=checked)
        self.switch.toggled.connect(lambda state: on_toggle(tweak.id, state))
        lay.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignTop)

        center = QVBoxLayout()
        center.setSpacing(5)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        name_lbl = QLabel(tweak.name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #FAFAFA;")
        name_lbl.setWordWrap(True)
        top_row.addWidget(name_lbl, 1)

        risk_styles = {
            "SAFE": ("rgba(16, 185, 129, 0.14)", "#34D399"),
            "MODERATE": ("rgba(245, 158, 11, 0.14)", "#FBBF24"),
            "ADVANCED": ("rgba(239, 68, 68, 0.14)", "#F87171"),
        }
        rbg, rfg = risk_styles.get(tweak.risk.value, ("#1F1F29", "#A1A1AA"))
        risk_pill = QLabel(tweak.risk.value)
        risk_pill.setStyleSheet(
            f"background-color: {rbg}; color: {rfg}; border-radius: 6px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )
        top_row.addWidget(risk_pill)

        src_pill = QLabel(tweak.source)
        src_pill.setStyleSheet(
            "background-color: #1D1D28; color: #A1A1AA; border-radius: 6px; padding: 2px 8px; font-size: 10px;"
        )
        top_row.addWidget(src_pill)
        center.addLayout(top_row)

        desc_lbl = QLabel(tweak.description)
        desc_lbl.setStyleSheet("color: #A1A1AA; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        center.addWidget(desc_lbl)
        lay.addLayout(center, 1)

        right = QVBoxLayout()
        right.setSpacing(6)
        btn_apply = QPushButton("Apply")
        btn_apply.setObjectName("PrimaryBtn")
        btn_apply.setFixedWidth(76)
        btn_apply.clicked.connect(lambda: on_apply(tweak))
        right.addWidget(btn_apply)

        if tweak.reversible:
            btn_rev = QPushButton("Revert")
            btn_rev.setObjectName("GhostBtn")
            btn_rev.setFixedWidth(76)
            btn_rev.clicked.connect(lambda: on_revert(tweak))
            right.addWidget(btn_rev)

        lay.addLayout(right)
