"""Read-only Windows Optimization Health Score inspector (0-100)."""

from __future__ import annotations

import winreg
from typing import Any


def _read_dword(root: int, subkey: str, name: str) -> int | None:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, name)
            return int(val)
    except (OSError, ValueError, TypeError):
        return None


def evaluate_optimization_score() -> dict[str, Any]:
    """Inspect key Windows optimization flags and return a 0-100 health score."""
    checks: list[dict[str, Any]] = [
        {
            "id": "telemetry",
            "name": "Windows Telemetry Disabled",
            "passed": _read_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                "AllowTelemetry",
            ) == 0,
            "hint": "Jalankan preset atau aktifkan 'Disable Windows Telemetry'.",
        },
        {
            "id": "copilot",
            "name": "Windows Copilot & AI Bloat Disabled",
            "passed": (
                _read_dword(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                    "TurnOffWindowsCopilot",
                ) == 1
                or _read_dword(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
                    "TurnOffWindowsCopilot",
                ) == 1
            ),
            "hint": "Nonaktifkan Copilot & AI Recall di Privacy & Debloat.",
        },
        {
            "id": "gamedvr",
            "name": "GameDVR Background Recording Off",
            "passed": _read_dword(
                winreg.HKEY_CURRENT_USER,
                r"System\GameConfigStore",
                "GameDVR_Enabled",
            ) == 0,
            "hint": "Matikan GameDVR untuk mencegah FPS drop & stutter.",
        },
        {
            "id": "hags",
            "name": "Hardware-Accelerated GPU Scheduling (HAGS)",
            "passed": _read_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers",
                "HwSchMode",
            ) == 2,
            "hint": "Aktifkan HAGS di GPU & Gaming.",
        },
        {
            "id": "power_throttling",
            "name": "CPU Power Throttling Disabled",
            "passed": _read_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling",
                "PowerThrottlingOff",
            ) == 1,
            "hint": "Matikan PowerThrottlingOff untuk responsivitas CPU maksimal.",
        },
        {
            "id": "priority_sep",
            "name": "Foreground Thread Scheduling Tuned",
            "passed": _read_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\PriorityControl",
                "Win32PrioritySeparation",
            ) in (38, 26),
            "hint": "Optimalkan Win32PrioritySeparation di CPU & Power.",
        },
        {
            "id": "bing_search",
            "name": "Start Menu Bing Web Search Off",
            "passed": _read_dword(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Search",
                "BingSearchEnabled",
            ) == 0,
            "hint": "Matikan Bing Search agar Start Menu lebih cepat.",
        },
        {
            "id": "edge_boost",
            "name": "Edge Startup Boost Disabled",
            "passed": _read_dword(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Edge",
                "StartupBoostEnabled",
            ) == 0,
            "hint": "Debloat Microsoft Edge untuk hemat RAM saat startup.",
        },
    ]

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)
    score = int(round((passed_count / total_count) * 100)) if total_count else 0

    if score >= 90:
        grade = "S"
    elif score >= 75:
        grade = "A"
    elif score >= 50:
        grade = "B"
    elif score >= 25:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": score,
        "grade": grade,
        "passed_count": passed_count,
        "total_count": total_count,
        "checks": checks,
    }
