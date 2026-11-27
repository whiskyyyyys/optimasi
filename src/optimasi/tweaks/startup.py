"""Windows Startup Programs enumerator and safe enable/disable manager."""

from __future__ import annotations

import winreg
from dataclasses import dataclass

_RUN_LOCATIONS = [
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"),
]


@dataclass
class StartupItem:
    hive: str
    name: str
    command: str
    enabled: bool


def list_startup_items() -> list[StartupItem]:
    """Enumerate HKCU and HKLM Run startup items and check StartupApproved state."""
    items: list[StartupItem] = []
    for hive_name, root, run_path, approved_path in _RUN_LOCATIONS:
        approved_map: dict[str, bool] = {}
        try:
            with winreg.OpenKey(root, approved_path, 0, winreg.KEY_READ) as ak:
                idx = 0
                while True:
                    try:
                        vname, vdata, _ = winreg.EnumValue(ak, idx)
                        idx += 1
                        if isinstance(vdata, (bytes, bytearray)) and len(vdata) >= 1:
                            # 0x02 or 0x06 == enabled; 0x03 == disabled
                            approved_map[vname] = vdata[0] in (2, 6, 0)
                    except OSError:
                        break
        except OSError:
            pass

        try:
            with winreg.OpenKey(root, run_path, 0, winreg.KEY_READ) as rk:
                idx = 0
                while True:
                    try:
                        vname, vdata, _ = winreg.EnumValue(rk, idx)
                        idx += 1
                        items.append(
                            StartupItem(
                                hive=hive_name,
                                name=vname,
                                command=str(vdata),
                                enabled=approved_map.get(vname, True),
                            )
                        )
                    except OSError:
                        break
        except OSError:
            continue
    return items


def set_startup_item_enabled(hive: str, name: str, enabled: bool, dry_run: bool = False) -> tuple[bool, str]:
    """Toggle a Windows startup item cleanly via StartupApproved\\Run binary state."""
    if dry_run:
        state = "enable" if enabled else "disable"
        return True, f"[DRY-RUN] Would {state} startup item '{name}' ({hive})"

    loc = next((x for x in _RUN_LOCATIONS if x[0] == hive), None)
    if not loc:
        return False, f"Unknown hive: {hive}"

    _, root, _, approved_path = loc
    # Windows StartupApproved uses 12-byte structure; first byte 0x02=enabled, 0x03=disabled
    payload = bytes([0x02 if enabled else 0x03] + [0x00] * 11)
    try:
        with winreg.CreateKeyEx(root, approved_path, 0, winreg.KEY_SET_VALUE) as ak:
            winreg.SetValueEx(ak, name, 0, winreg.REG_BINARY, payload)
        return True, f"Startup item '{name}' {'enabled' if enabled else 'disabled'}."
    except OSError as exc:
        return False, f"Failed to update '{name}' (may require Admin): {exc}"
