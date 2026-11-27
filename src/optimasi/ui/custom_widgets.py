"""Custom PySide6 widgets: CircularScoreGauge, SparklineChart, ToggleSwitch, UpdateBanner, UpdateDialog, TweakCard."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, QThread, Signal
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
    """Animated pill toggle switch."""

    def __init__(self, checked: bool = False, accent: str = "#06B6D4", parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._accent = QColor(accent)
        self._pos = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"thumbPos", self)
        self._anim.setDuration(150)
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
        track_color = self._accent if self.isChecked() else QColor("#24324A")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, r.width(), r.height()), 12, 12)

        knob_d = 18
        x = 3 + self._pos * (r.width() - knob_d - 6)
        p.setBrush(QColor("#F8FAFC"))
        p.drawEllipse(QRectF(x, 3, knob_d, knob_d))


class CircularScoreGauge(QWidget):
    """Animated circular Optimization Health Score gauge (0-100)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(134, 134)
        self._score = 0.0
        self._grade = "—"
        self._anim = QPropertyAnimation(self, b"scoreValue", self)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_score(self) -> float:
        return self._score

    def _set_score(self, val: float) -> None:
        self._score = val
        self.update()

    scoreValue = Property(float, _get_score, _set_score)

    def set_score(self, score: int, grade: str) -> None:
        self._grade = grade
        self._anim.stop()
        self._anim.setStartValue(self._score)
        self._anim.setEndValue(float(max(0, min(100, score))))
        self._anim.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = 12
        rect = QRectF(margin, margin, self.width() - 2 * margin, self.height() - 2 * margin)

        # Track ring
        bg_pen = QPen(QColor("#1D2A42"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        # Active arc
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#06B6D4"))
        grad.setColorAt(1.0, QColor("#10B981"))
        fg_pen = QPen(grad, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(fg_pen)
        span = -int((self._score / 100.0) * 360 * 16)
        p.drawArc(rect, 90 * 16, span)

        # Score number
        p.setPen(QColor("#F8FAFC"))
        p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        p.drawText(QRectF(0, 26, self.width(), 44), Qt.AlignmentFlag.AlignCenter, f"{int(round(self._score))}")

        # Grade subtitle
        p.setPen(QColor("#22D3EE"))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(QRectF(0, 72, self.width(), 24), Qt.AlignmentFlag.AlignCenter, f"GRADE {self._grade}")


class SparklineChart(QWidget):
    """Real-time rolling sparkline area chart for CPU / RAM / Network."""

    def __init__(self, line_color: str = "#06B6D4", max_points: int = 36, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(52)
        self.setMaximumHeight(64)
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
        c_top.setAlpha(90)
        c_bot = QColor(self._color)
        c_bot.setAlpha(5)
        fill_grad.setColorAt(0.0, c_top)
        fill_grad.setColorAt(1.0, c_bot)
        p.fillPath(fill_path, fill_grad)

        p.setPen(QPen(self._color, 2.0))
        p.drawPath(line_path)


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
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #22D3EE;")
        lay.addWidget(title)

        sub = QLabel(f"Versi saat ini: v{update.current_version}  ->  Paket: {update.asset_name}")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lay.addWidget(sub)

        notes = QTextBrowser()
        notes.setStyleSheet("background-color: #0E1524; border: 1px solid #1E2B42; border-radius: 8px; padding: 8px; color: #E2E8F0;")
        notes.setMarkdown(update.changelog)
        lay.addWidget(notes, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
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
    """Modern Fluent card representing an individual Windows tweak."""

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
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        self.switch = ToggleSwitch(checked=checked)
        self.switch.toggled.connect(lambda state: on_toggle(tweak.id, state))
        lay.addWidget(self.switch, 0, Qt.AlignmentFlag.AlignTop)

        center = QVBoxLayout()
        center.setSpacing(4)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        name_lbl = QLabel(tweak.name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #F8FAFC;")
        name_lbl.setWordWrap(True)
        top_row.addWidget(name_lbl, 1)

        risk_styles = {
            "SAFE": ("#064E3B", "#34D399"),
            "MODERATE": ("#451A03", "#FBBF24"),
            "ADVANCED": ("#450A0A", "#F87171"),
        }
        rbg, rfg = risk_styles.get(tweak.risk.value, ("#1E293B", "#94A3B8"))
        risk_pill = QLabel(tweak.risk.value)
        risk_pill.setStyleSheet(
            f"background-color: {rbg}; color: {rfg}; border-radius: 6px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )
        top_row.addWidget(risk_pill)

        src_pill = QLabel(tweak.source)
        src_pill.setStyleSheet(
            "background-color: #1A2438; color: #94A3B8; border-radius: 6px; padding: 2px 8px; font-size: 10px;"
        )
        top_row.addWidget(src_pill)
        center.addLayout(top_row)

        desc_lbl = QLabel(tweak.description)
        desc_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        center.addWidget(desc_lbl)
        lay.addLayout(center, 1)

        right = QVBoxLayout()
        right.setSpacing(6)
        btn_apply = QPushButton("Apply")
        btn_apply.setObjectName("PrimaryBtn")
        btn_apply.setFixedWidth(74)
        btn_apply.clicked.connect(lambda: on_apply(tweak))
        right.addWidget(btn_apply)

        if tweak.reversible:
            btn_rev = QPushButton("Revert")
            btn_rev.setObjectName("GhostBtn")
            btn_rev.setFixedWidth(74)
            btn_rev.clicked.connect(lambda: on_revert(tweak))
            right.addWidget(btn_rev)

        lay.addLayout(right)
