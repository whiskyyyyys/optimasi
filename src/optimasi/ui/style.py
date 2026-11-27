"""Modern Windows 11 Dark Fluent stylesheet and DWM dark titlebar helper."""

from __future__ import annotations

import ctypes

DARK_QSS = """
QMainWindow, QDialog {
    background-color: #090D16;
    color: #F1F5F9;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #F1F5F9;
    font-family: "Segoe UI", sans-serif;
}

#Sidebar {
    background-color: #0E1422;
    border-right: 1px solid #1C263B;
}

#BrandTitle {
    font-size: 20px;
    font-weight: 700;
    color: #22D3EE;
    letter-spacing: 1px;
}

#BrandSub {
    font-size: 11px;
    color: #64748B;
}

QPushButton#NavBtn {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 8px;
    padding: 9px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#NavBtn:hover {
    background-color: #151E32;
    color: #E2E8F0;
}

QPushButton#NavBtn[active="true"] {
    background-color: #162338;
    color: #22D3EE;
    border-left: 3px solid #06B6D4;
}

#HeaderBar {
    background-color: #0E1422;
    border-bottom: 1px solid #1C263B;
}

#PageTitle {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
}

QLineEdit#SearchBox {
    background-color: #090D16;
    border: 1px solid #23314A;
    border-radius: 8px;
    padding: 6px 12px;
    color: #F1F5F9;
    font-size: 12px;
}

QLineEdit#SearchBox:focus {
    border: 1px solid #06B6D4;
}

QFrame#Card {
    background-color: #121A2B;
    border: 1px solid #1E2B42;
    border-radius: 12px;
}

QFrame#HeroCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111C33, stop:1 #0E1729);
    border: 1px solid #243859;
    border-radius: 14px;
}

QFrame#FeaturedPresetCard {
    background-color: #121D31;
    border: 1px solid #06B6D4;
    border-radius: 12px;
}

QFrame#UpdateBanner {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #083344, stop:1 #0F2942);
    border: 1px solid #06B6D4;
    border-radius: 10px;
}

QPushButton#PrimaryBtn {
    background-color: #06B6D4;
    color: #04101B;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#PrimaryBtn:hover {
    background-color: #22D3EE;
}

QPushButton#PrimaryBtn:disabled {
    background-color: #1E293B;
    color: #64748B;
}

QPushButton#SuccessBtn {
    background-color: #10B981;
    color: #04150E;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#SuccessBtn:hover {
    background-color: #34D399;
}

QPushButton#WarningBtn {
    background-color: #78350F;
    color: #FDE68A;
    border: 1px solid #B45309;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#WarningBtn:hover {
    background-color: #92400E;
}

QPushButton#DangerBtn {
    background-color: #7F1D1D;
    color: #FECACA;
    border: 1px solid #B91C1C;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#DangerBtn:hover {
    background-color: #991B1B;
}

QPushButton#GhostBtn {
    background-color: #192338;
    color: #E2E8F0;
    border: 1px solid #26344F;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#GhostBtn:hover {
    background-color: #22304D;
    border-color: #38BDF8;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: #0B101B;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #25344E;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #06B6D4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QPlainTextEdit#ConsoleBox {
    background-color: #060911;
    color: #CBD5E1;
    border: 1px solid #1C263B;
    border-radius: 8px;
    font-family: "Consolas", monospace;
    font-size: 11px;
    padding: 6px;
}

QProgressBar {
    background-color: #090D16;
    border: 1px solid #1E2B42;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 10px;
    color: #F8FAFC;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:1 #10B981);
    border-radius: 5px;
}

QTableWidget {
    background-color: #0E1524;
    alternate-background-color: #111A2C;
    border: 1px solid #1E2B42;
    border-radius: 10px;
    gridline-color: #1B273D;
    color: #E2E8F0;
    selection-background-color: #164E63;
}

QHeaderView::section {
    background-color: #141D30;
    color: #94A3B8;
    padding: 7px 10px;
    border: none;
    border-bottom: 1px solid #1E2B42;
    font-weight: 700;
    font-size: 11px;
}

QTabWidget::pane {
    border: none;
}

QTabBar::tab {
    background-color: #121A2B;
    color: #94A3B8;
    border: 1px solid #1E2B42;
    padding: 7px 16px;
    border-radius: 8px;
    margin-right: 6px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #162840;
    color: #22D3EE;
    border-color: #06B6D4;
}

QCheckBox {
    spacing: 8px;
    color: #E2E8F0;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #3B4E70;
    background-color: #0A0F1A;
}

QCheckBox::indicator:checked {
    background-color: #06B6D4;
    border-color: #22D3EE;
}
"""


def apply_windows_dark_titlebar(hwnd: int) -> None:
    """Enable native Windows 11/10 immersive dark titlebar via DWM API."""
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(val),
            ctypes.sizeof(val),
        )
    except Exception:
        pass
