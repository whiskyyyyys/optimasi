"""1-Click Game/Emulator Booster & Laptop AC/DC Thermal Power Controller."""

from __future__ import annotations

import re
import subprocess
from typing import Callable

from optimasi.core.cleaner import trim_ram_working_sets

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def get_active_power_guid() -> str | None:
    """Return GUID of the currently active Windows power scheme."""
    try:
        res = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_CREATE_NO_WINDOW,
        )
        m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", res.stdout or "")
        return m.group(1) if m else None
    except Exception:
        return None


class GameBooster:
    """Manages temporary High-Performance boost state + instant restore."""

    def __init__(self) -> None:
        self.active: bool = False
        self.previous_plan_guid: str | None = None

    def activate_boost(
        self,
        dry_run: bool = False,
        log_cb: Callable[[str], None] | None = None,
    ) -> dict:
        def log(msg: str) -> None:
            if log_cb:
                log_cb(msg)

        prev_guid = get_active_power_guid()
        if not self.active and prev_guid:
            self.previous_plan_guid = prev_guid

        if dry_run:
            trimmed, _ = trim_ram_working_sets(dry_run=True, log_cb=log)
            log("[DRY-RUN] Would activate High Performance power plan & flush DNS cache.")
            self.active = True
            return {
                "active": True,
                "processes_trimmed": trimmed,
                "previous_plan_guid": self.previous_plan_guid,
            }

        # Try High Performance (8c5e7fda...) or Ultimate Performance
        subprocess.run(
            ["powercfg", "-setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
        )
        trimmed, _ = trim_ram_working_sets(dry_run=False, log_cb=log)
        subprocess.run(["ipconfig", "/flushdns"], capture_output=True, creationflags=_CREATE_NO_WINDOW)
        self.active = True
        log("Game & Emulator Boost ACTIVE (Power Plan boosted, RAM trimmed, DNS flushed).")
        return {
            "active": True,
            "processes_trimmed": trimmed,
            "previous_plan_guid": self.previous_plan_guid,
        }

    def restore_boost(
        self,
        dry_run: bool = False,
        log_cb: Callable[[str], None] | None = None,
    ) -> tuple[bool, str]:
        def log(msg: str) -> None:
            if log_cb:
                log_cb(msg)

        target_guid = self.previous_plan_guid or "381b4222-f694-41f0-9685-ff5bb260df2e"
        if dry_run:
            self.active = False
            msg = f"[DRY-RUN] Would restore power plan GUID {target_guid}."
            log(msg)
            return True, msg

        subprocess.run(
            ["powercfg", "-setactive", target_guid],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
        )
        self.active = False
        msg = f"Restored power plan ({target_guid})."
        log(msg)
        return True, msg


def set_laptop_thermal_mode(
    mode: str,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Configure Laptop AC (plugged-in) and DC (battery) CPU max throttle & parking."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    profiles = {
        "cool_quiet": ("Cool & Quiet (99% AC / 80% DC)", 99, 80, 50, 10),
        "balanced_laptop": ("Balanced Laptop (100% AC / 85% DC)", 100, 85, 100, 15),
        "max_turbo": ("Max Turbo Performance (100% AC / 100% DC)", 100, 100, 100, 100),
    }
    if mode not in profiles:
        return False, f"Unknown thermal mode: {mode}"

    label, ac_max, dc_max, ac_cores, dc_cores = profiles[mode]
    if dry_run:
        msg = f"[DRY-RUN] Would apply Laptop Thermal Mode '{label}' (AC={ac_max}%, DC={dc_max}%)."
        log(msg)
        return True, msg

    cmds = [
        ["powercfg", "-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", str(ac_max)],
        ["powercfg", "-setdcvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", str(dc_max)],
        ["powercfg", "-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", str(ac_cores)],
        ["powercfg", "-setdcvalueindex", "scheme_current", "sub_processor", "CPMINCORES", str(dc_cores)],
        ["powercfg", "-setactive", "scheme_current"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, capture_output=True, creationflags=_CREATE_NO_WINDOW)

    msg = f"Applied Laptop Thermal Mode: {label}."
    log(msg)
    return True, msg
