"""Sleek Obsidian / Zinc Fluent dark stylesheet and DWM dark titlebar helper."""

from __future__ import annotations

import ctypes

DARK_QSS = """
QMainWindow, QDialog {
    background-color: #09090B;
    color: #FAFAFA;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QWidget {
    color: #FAFAFA;
    font-family: "Segoe UI", sans-serif;
}

#Sidebar {
    background-color: #0D0D12;
    border-right: 1px solid #1C1C24;
}

#BrandTitle {
    font-size: 19px;
    font-weight: 800;
    color: #38BDF8;
    letter-spacing: 1.5px;
}

#BrandSub {
    font-size: 11px;
    color: #71717A;
}

QPushButton#NavBtn {
    background-color: transparent;
    color: #A1A1AA;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 9px;
    padding: 9px 13px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
}

QPushButton#NavBtn:hover {
    background-color: #16161F;
    color: #F4F4F5;
}

QPushButton#NavBtn[active="true"] {
    background-color: rgba(56, 189, 248, 0.10);
    color: #38BDF8;
    border-left: 3px solid #38BDF8;
}

#HeaderBar {
    background-color: #0D0D12;
    border-bottom: 1px solid #1C1C24;
}

#PageTitle {
    font-size: 18px;
    font-weight: 700;
    color: #FAFAFA;
}

QLineEdit#SearchBox {
    background-color: #13131A;
    border: 1px solid #252532;
    border-radius: 9px;
    padding: 7px 14px;
    color: #FAFAFA;
    font-size: 12px;
}

QLineEdit#SearchBox:focus {
    border: 1px solid #38BDF8;
    background-color: #161620;
}

QFrame#Card {
    background-color: #13131A;
    border: 1px solid #22222C;
    border-radius: 14px;
}

QFrame#Card:hover {
    border: 1px solid #30303E;
}

QFrame#HeroCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #151726, stop:1 #0F131E);
    border: 1px solid #282B3E;
    border-radius: 16px;
}

QFrame#FeaturedPresetCard {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #131A29, stop:1 #111520);
    border: 1px solid #0284C7;
    border-radius: 14px;
}

QFrame#UpdateBanner {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0C2A3E, stop:1 #14223B);
    border: 1px solid #38BDF8;
    border-radius: 10px;
}

QFrame#StatusBarFrame {
    background-color: #0D0D12;
    border-top: 1px solid #1C1C24;
}

QFrame#ToastFrame {
    background-color: #181822;
    border: 1px solid #38BDF8;
    border-radius: 10px;
}

QPushButton#PrimaryBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #06B6D4);
    color: #030712;
    border: none;
    border-radius: 8px;
    padding: 7px 15px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#PrimaryBtn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38BDF8, stop:1 #22D3EE);
}

QPushButton#PrimaryBtn:disabled {
    background-color: #1F1F29;
    color: #52525B;
}

QPushButton#SuccessBtn {
    background-color: rgba(16, 185, 129, 0.18);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.40);
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#SuccessBtn:hover {
    background-color: rgba(16, 185, 129, 0.28);
}

QPushButton#WarningBtn {
    background-color: rgba(245, 158, 11, 0.16);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.38);
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#WarningBtn:hover {
    background-color: rgba(245, 158, 11, 0.26);
}

QPushButton#DangerBtn {
    background-color: rgba(239, 68, 68, 0.16);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 700;
    font-size: 12px;
}

QPushButton#DangerBtn:hover {
    background-color: rgba(239, 68, 68, 0.28);
}

QPushButton#GhostBtn {
    background-color: #1A1A24;
    color: #E4E4E7;
    border: 1px solid #2A2A38;
    border-radius: 8px;
    padding: 6px 13px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton#GhostBtn:hover {
    background-color: #232330;
    border-color: #38BDF8;
}

QComboBox {
    background-color: #1A1A24;
    border: 1px solid #2A2A38;
    border-radius: 8px;
    padding: 5px 12px;
    color: #FAFAFA;
    font-size: 12px;
    min-width: 100px;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QComboBox QAbstractItemView {
    background-color: #15151E;
    border: 1px solid #2A2A38;
    color: #FAFAFA;
    selection-background-color: #0284C7;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
}

QScrollBar::handle:vertical {
    background: #272734;
    min-height: 28px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #38BDF8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QPlainTextEdit#ConsoleBox {
    background-color: #09090D;
    color: #D4D4D8;
    border: 1px solid #1E1E28;
    border-radius: 8px;
    font-family: "Consolas", monospace;
    font-size: 11px;
    padding: 8px;
}

QProgressBar {
    background-color: #1A1A24;
    border: 1px solid #252532;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    font-size: 10px;
    color: #FAFAFA;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0EA5E9, stop:1 #10B981);
    border-radius: 4px;
}

QTableWidget {
    background-color: #111118;
    alternate-background-color: #15151E;
    border: 1px solid #22222C;
    border-radius: 12px;
    gridline-color: #1C1C26;
    color: #F4F4F5;
    selection-background-color: rgba(56, 189, 248, 0.20);
}

QHeaderView::section {
    background-color: #161620;
    color: #A1A1AA;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #22222C;
    font-weight: 700;
    font-size: 11px;
}

QCheckBox {
    spacing: 8px;
    color: #E4E4E7;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid #3F3F4E;
    background-color: #0D0D12;
}

QCheckBox::indicator:checked {
    background-color: #0EA5E9;
    border-color: #38BDF8;
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
