"""Backup, System Restore Point, and Session Undo management."""

from __future__ import annotations

import json
import os
import subprocess
import winreg
from datetime import datetime
from pathlib import Path
from typing import Callable

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

_HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}


def get_backup_root() -> Path:
    """Return the user's Optimasi backup directory."""
    user_profile = Path(os.environ.get("USERPROFILE", Path.home()))
    root = user_profile / "Documents" / "OptimasiBackups"
    return root


def get_sessions_dir() -> Path:
    return get_backup_root() / "sessions"


def create_restore_point(
    description: str = "OptimasiWindowsRestorePoint",
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Create a Windows System Restore Point via PowerShell."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    if dry_run:
        msg = f"[DRY-RUN] Would create System Restore Point: {description}"
        log(msg)
        return True, msg

    ps_script = (
        "$ErrorActionPreference = 'Stop'; "
        "try { Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue } catch {}; "
        "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\SystemRestore' "
        "-Name 'SystemRestorePointCreationFrequency' -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue; "
        f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'"
    )
    log(f"Creating Windows System Restore Point: {description}...")
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=120,
            creationflags=_CREATE_NO_WINDOW,
        )
        if res.returncode == 0:
            msg = f"System Restore Point '{description}' created successfully."
            log(msg)
            return True, msg
        err = (res.stderr or res.stdout or "Unknown error").strip()
        msg = f"Restore Point failed (requires Admin / System Protection enabled): {err}"
        log(msg)
        return False, msg
    except Exception as exc:
        msg = f"Restore Point error: {exc}"
        log(msg)
        return False, msg


def export_registry_backup(
    target_dir: Path | str | None = None,
    full: bool = False,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Export key Windows Registry hives to a timestamped backup folder."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(target_dir) if target_dir else (get_backup_root() / f"registry_{stamp}")

    targets = (
        [
            ("HKLM.reg", "HKLM"),
            ("HKCU.reg", "HKCU"),
        ]
        if full
        else [
            ("HKLM_Control.reg", r"HKLM\SYSTEM\CurrentControlSet\Control"),
            ("HKLM_Policies.reg", r"HKLM\SOFTWARE\Policies"),
            ("HKLM_Multimedia.reg", r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia"),
            ("HKCU_ControlPanel.reg", r"HKCU\Control Panel"),
            ("HKCU_WinCurrentVersion.reg", r"HKCU\Software\Microsoft\Windows\CurrentVersion"),
        ]
    )

    if dry_run:
        msg = f"[DRY-RUN] Would export {len(targets)} registry hive snapshots to {dest}"
        log(msg)
        return True, msg

    dest.mkdir(parents=True, exist_ok=True)
    exported = 0
    errors: list[str] = []
    for filename, reg_path in targets:
        out_file = dest / filename
        log(f"Exporting {reg_path} -> {out_file.name}...")
        try:
            res = subprocess.run(
                ["reg", "export", reg_path, str(out_file), "/y"],
                capture_output=True,
                text=True,
                timeout=180 if full else 30,
                creationflags=_CREATE_NO_WINDOW,
            )
            if res.returncode == 0 and out_file.exists():
                exported += 1
            else:
                errors.append(f"{reg_path}: {(res.stderr or res.stdout).strip()}")
        except Exception as exc:
            errors.append(f"{reg_path}: {exc}")

    if exported == len(targets):
        msg = f"Registry backup saved ({exported} files) at: {dest}"
        log(msg)
        return True, msg
    if exported > 0:
        msg = f"Partial registry backup ({exported}/{len(targets)}) at {dest}. Notes: {'; '.join(errors)}"
        log(msg)
        return True, msg
    msg = f"Registry backup failed: {'; '.join(errors)}"
    log(msg)
    return False, msg


def list_undo_sessions() -> list[dict]:
    """List recorded tweak undo sessions newest-first."""
    sdir = get_sessions_dir()
    if not sdir.exists():
        return []
    sessions: list[dict] = []
    for path in sorted(sdir.glob("session_*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "timestamp": data.get("timestamp", ""),
                    "label": data.get("label", path.stem),
                    "entry_count": len(data.get("entries", [])),
                }
            )
        except Exception:
            continue
    return sessions


def _restore_reg_entry(entry: dict) -> str:
    root = _HIVE_MAP[entry["hive"]]
    subkey = entry["subkey"]
    name = entry.get("name")
    existed = entry.get("existed", False)
    if not existed:
        if name is None:
            winreg.DeleteKey(root, subkey)
            return f"Deleted created key {entry['hive']}\\{subkey}"
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
        return f"Removed added value {entry['hive']}\\{subkey} [{name}]"

    prev_type = entry["prev_type"]
    prev_val = entry["prev_value"]
    if prev_type == winreg.REG_BINARY and isinstance(prev_val, str):
        prev_val = bytes.fromhex(prev_val)
    with winreg.CreateKeyEx(root, subkey, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, prev_type, prev_val)
    return f"Restored {entry['hive']}\\{subkey} [{name or '(Default)'}]"


def revert_session(
    session_path: str | Path,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Revert recorded registry and service changes from a session JSON file."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    path = Path(session_path)
    if not path.exists():
        return False, f"Session file not found: {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    entries = list(reversed(data.get("entries", [])))
    if not entries:
        return True, "No revertible entries in this session."

    reverted = 0
    errors = 0
    for entry in entries:
        kind = entry.get("kind")
        if dry_run:
            log(f"[DRY-RUN] Would revert {kind}: {entry}")
            reverted += 1
            continue
        try:
            if kind == "reg":
                msg = _restore_reg_entry(entry)
                log(msg)
                reverted += 1
            elif kind == "service":
                svc = entry["service_name"]
                prev_start = entry["prev_start"]
                subprocess.run(
                    ["sc", "config", svc, f"start= {prev_start}"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=_CREATE_NO_WINDOW,
                )
                log(f"Restored service {svc} start={prev_start}")
                reverted += 1
        except Exception as exc:
            errors += 1
            log(f"Revert warning ({kind}): {exc}")

    return errors == 0, f"Reverted {reverted} changes ({errors} warnings)."
