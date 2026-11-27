"""Safe Windows tweak execution engine with Dry-Run and Undo logging."""

from __future__ import annotations

import json
import os
import subprocess
import winreg
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from optimasi.core.backup import get_sessions_dir
from optimasi.tweaks.models import (
    Action,
    AppxRemove,
    Cmd,
    DnsSet,
    FunctionAction,
    HostsBlock,
    PowerCfg,
    PowerShell,
    RegDelete,
    RegSet,
    ScheduledTask,
    ServiceConfig,
    Tweak,
)

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}

REG_TYPE_MAP = {
    "REG_DWORD": winreg.REG_DWORD,
    "REG_SZ": winreg.REG_SZ,
    "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
    "REG_QWORD": winreg.REG_QWORD,
    "REG_BINARY": winreg.REG_BINARY,
}

HOSTS_BEGIN_MARKER = "# BEGIN OPTIMASI TELEMETRY BLOCK"
HOSTS_END_MARKER = "# END OPTIMASI TELEMETRY BLOCK"
DEFAULT_HOSTS_PATH = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"


def apply_hosts_block(
    domains: list[str],
    hosts_path: Path | str | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Idempotently write or update the managed telemetry block in the hosts file."""
    target = Path(hosts_path) if hosts_path else DEFAULT_HOSTS_PATH
    existing = target.read_text(encoding="utf-8", errors="ignore") if target.exists() else ""

    cleaned = _strip_hosts_block(existing)
    unique_domains = list(dict.fromkeys(d.strip() for d in domains if d.strip()))
    block_lines = [HOSTS_BEGIN_MARKER]
    for dom in unique_domains:
        block_lines.append(f"0.0.0.0\t{dom}")
    block_lines.append(HOSTS_END_MARKER)
    block_text = "\n".join(block_lines)

    new_content = (cleaned.rstrip() + "\n\n" + block_text + "\n") if cleaned.strip() else (block_text + "\n")

    if dry_run:
        return True, f"[DRY-RUN] Would block {len(unique_domains)} telemetry domains in {target}"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")
    return True, f"Blocked {len(unique_domains)} telemetry domains in {target}"


def remove_hosts_block(
    hosts_path: Path | str | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Remove the managed telemetry block from the hosts file."""
    target = Path(hosts_path) if hosts_path else DEFAULT_HOSTS_PATH
    if not target.exists():
        return True, "Hosts file does not exist; nothing to remove."
    existing = target.read_text(encoding="utf-8", errors="ignore")
    cleaned = _strip_hosts_block(existing)
    if dry_run:
        return True, f"[DRY-RUN] Would remove Optimasi telemetry block from {target}"
    target.write_text(cleaned, encoding="utf-8")
    return True, f"Removed Optimasi telemetry block from {target}"


def _strip_hosts_block(content: str) -> str:
    lines = content.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped == HOSTS_BEGIN_MARKER:
            skipping = True
            continue
        if stripped == HOSTS_END_MARKER:
            skipping = False
            continue
        if not skipping:
            out.append(line)
    result = "\n".join(out).rstrip()
    return (result + "\n") if result else ""


def _parse_reg_value(value: Any, reg_type_name: str) -> tuple[int, Any]:
    rtype = REG_TYPE_MAP[reg_type_name]
    if rtype in (winreg.REG_DWORD, winreg.REG_QWORD):
        if isinstance(value, str):
            return rtype, int(value, 0)
        return rtype, int(value)
    if rtype == winreg.REG_BINARY:
        if isinstance(value, (bytes, bytearray)):
            return rtype, bytes(value)
        if isinstance(value, str):
            return rtype, bytes.fromhex(value.replace(" ", "").replace(",", ""))
    return rtype, str(value)


def _query_service_start_type(service_name: str) -> str | None:
    try:
        res = subprocess.run(
            ["sc", "qc", service_name],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_CREATE_NO_WINDOW,
        )
        if res.returncode != 0:
            return None
        for line in res.stdout.splitlines():
            if "START_TYPE" in line:
                upper = line.upper()
                if "DISABLED" in upper:
                    return "disabled"
                if "DEMAND_START" in upper:
                    return "demand"
                if "AUTO_START" in upper and "DELAYED" in upper:
                    return "delayed-auto"
                if "AUTO_START" in upper:
                    return "auto"
    except Exception:
        pass
    return None


@dataclass
class ExecutionResult:
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    logs: list[str] = field(default_factory=list)
    session_file: str | None = None


class TweakExecutor:
    """Executes Tweak actions with Dry-Run simulation and Undo recording."""

    def __init__(self, dry_run: bool = False, log_cb: Callable[[str], None] | None = None):
        self.dry_run = dry_run
        self.log_cb = log_cb

    def _log(self, message: str, logs: list[str]) -> None:
        logs.append(message)
        if self.log_cb:
            self.log_cb(message)

    def run_tweaks(
        self,
        tweaks: list[Tweak],
        revert: bool = False,
        session_label: str = "Tweak Run",
    ) -> ExecutionResult:
        result = ExecutionResult()
        undo_entries: list[dict[str, Any]] = []
        mode_tag = "REVERT" if revert else "APPLY"

        for tweak in tweaks:
            actions = tweak.revert_actions if revert else tweak.apply_actions
            if not actions:
                self._log(f"[{mode_tag}] Skipping '{tweak.name}' (no actions defined).", result.logs)
                result.skipped += 1
                continue

            self._log(f"=== [{mode_tag}] {tweak.name} ===", result.logs)
            for action in actions:
                ok, msg = self._run_action(action, undo_entries)
                self._log(f"  {msg}", result.logs)
                if ok:
                    result.succeeded += 1
                else:
                    result.failed += 1

        if undo_entries and not self.dry_run and not revert:
            try:
                sdir = get_sessions_dir()
                sdir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                spath = sdir / f"session_{stamp}.json"
                payload = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "label": session_label,
                    "tweak_ids": [t.id for t in tweaks],
                    "entries": undo_entries,
                }
                spath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                result.session_file = str(spath)
                self._log(f"Undo snapshot saved: {spath.name} ({len(undo_entries)} items)", result.logs)
            except Exception as exc:
                self._log(f"Warning: could not save undo snapshot: {exc}", result.logs)

        return result

    def _run_action(self, action: Action, undo_entries: list[dict[str, Any]]) -> tuple[bool, str]:
        if self.dry_run:
            if isinstance(action, FunctionAction):
                msgs = action.fn(dry_run=True, log_cb=None)
                detail = "; ".join(msgs[:2]) if msgs else action.describe()
                return True, f"[DRY-RUN] {detail}"
            return True, f"[DRY-RUN] {action.describe()}"

        try:
            if isinstance(action, RegSet):
                return self._exec_reg_set(action, undo_entries)
            if isinstance(action, RegDelete):
                return self._exec_reg_delete(action, undo_entries)
            if isinstance(action, ServiceConfig):
                return self._exec_service(action, undo_entries)
            if isinstance(action, PowerCfg):
                return self._exec_cmd(["powercfg", *action.args], shell=False, ignore_errors=True)
            if isinstance(action, Cmd):
                return self._exec_cmd(action.command, shell=action.shell, ignore_errors=action.ignore_errors)
            if isinstance(action, PowerShell):
                return self._exec_cmd(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", action.script],
                    shell=False,
                    ignore_errors=action.ignore_errors,
                )
            if isinstance(action, ScheduledTask):
                flag = "/Enable" if action.enabled else "/Disable"
                return self._exec_cmd(["schtasks", "/Change", "/TN", action.task_path, flag], shell=False, ignore_errors=True)
            if isinstance(action, HostsBlock):
                if action.enable:
                    return apply_hosts_block(action.domains, dry_run=False)
                return remove_hosts_block(dry_run=False)
            if isinstance(action, DnsSet):
                return self._exec_dns(action)
            if isinstance(action, AppxRemove):
                return self._exec_appx_remove(action)
            if isinstance(action, FunctionAction):
                msgs = action.fn(dry_run=False, log_cb=self.log_cb)
                return True, "; ".join(msgs) if msgs else f"Completed: {action.label}"
            return False, f"Unsupported action type: {type(action).__name__}"
        except Exception as exc:
            return False, f"Error ({action.describe()}): {exc}"

    def _exec_reg_set(self, action: RegSet, undo_entries: list[dict[str, Any]]) -> tuple[bool, str]:
        root = HIVE_MAP[action.hive]
        reg_type, parsed_val = _parse_reg_value(action.value, action.reg_type)
        val_name = action.name if action.name != "@" else ""

        existed = False
        prev_type = None
        prev_val = None
        try:
            with winreg.OpenKey(root, action.subkey, 0, winreg.KEY_READ) as key:
                prev_val, prev_type = winreg.QueryValueEx(key, val_name)
                existed = True
        except OSError:
            pass

        with winreg.CreateKeyEx(root, action.subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, val_name, 0, reg_type, parsed_val)

        if existed and prev_type == winreg.REG_BINARY and isinstance(prev_val, bytes):
            prev_val = prev_val.hex()
        undo_entries.append(
            {
                "kind": "reg",
                "hive": action.hive,
                "subkey": action.subkey,
                "name": val_name,
                "existed": existed,
                "prev_type": prev_type,
                "prev_value": prev_val,
            }
        )
        return True, f"Applied: {action.describe()}"

    def _exec_reg_delete(self, action: RegDelete, undo_entries: list[dict[str, Any]]) -> tuple[bool, str]:
        root = HIVE_MAP[action.hive]
        if action.name is None:
            try:
                winreg.DeleteKey(root, action.subkey)
                return True, f"Deleted key: {action.hive}\\{action.subkey}"
            except FileNotFoundError:
                return True, f"Key not present (skipped): {action.hive}\\{action.subkey}"
        try:
            with winreg.OpenKey(root, action.subkey, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
                prev_val, prev_type = winreg.QueryValueEx(key, action.name)
                winreg.DeleteValue(key, action.name)
            if prev_type == winreg.REG_BINARY and isinstance(prev_val, bytes):
                prev_val = prev_val.hex()
            undo_entries.append(
                {
                    "kind": "reg",
                    "hive": action.hive,
                    "subkey": action.subkey,
                    "name": action.name,
                    "existed": True,
                    "prev_type": prev_type,
                    "prev_value": prev_val,
                }
            )
            return True, f"Deleted value: {action.hive}\\{action.subkey} [{action.name}]"
        except FileNotFoundError:
            return True, f"Value not present (skipped): {action.hive}\\{action.subkey} [{action.name}]"

    def _exec_service(self, action: ServiceConfig, undo_entries: list[dict[str, Any]]) -> tuple[bool, str]:
        prev_start = _query_service_start_type(action.service_name)
        res = subprocess.run(
            ["sc", "config", action.service_name, f"start= {action.start_type}"],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_CREATE_NO_WINDOW,
        )
        if prev_start and res.returncode == 0:
            undo_entries.append(
                {
                    "kind": "service",
                    "service_name": action.service_name,
                    "prev_start": prev_start,
                }
            )
        if action.state == "stopped":
            subprocess.run(
                ["sc", "stop", action.service_name],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=_CREATE_NO_WINDOW,
            )
        elif action.state == "running":
            subprocess.run(
                ["sc", "start", action.service_name],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=_CREATE_NO_WINDOW,
            )
        if res.returncode == 0:
            return True, f"Service configured: {action.service_name} -> {action.start_type}"
        return True, f"Service note ({action.service_name}): {(res.stdout or res.stderr).strip()}"

    def _exec_cmd(self, command: str | list[str], shell: bool, ignore_errors: bool) -> tuple[bool, str]:
        res = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=_CREATE_NO_WINDOW,
        )
        out = (res.stdout or res.stderr or "").strip().splitlines()
        summary = out[0][:120] if out else f"exit={res.returncode}"
        cmd_label = command if isinstance(command, str) else " ".join(command[:3])
        if res.returncode == 0 or ignore_errors:
            return True, f"Executed ({cmd_label}): {summary}"
        return False, f"Failed ({cmd_label}): {summary}"

    def _exec_dns(self, action: DnsSet) -> tuple[bool, str]:
        if action.primary is None:
            script = (
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }"
            )
        else:
            servers = f"@('{action.primary}','{action.secondary}')" if action.secondary else f"@('{action.primary}')"
            script = (
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                f"ForEach-Object {{ Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ServerAddresses {servers} }}"
            )
        ok, msg = self._exec_cmd(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            shell=False,
            ignore_errors=False,
        )
        if ok:
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True, creationflags=_CREATE_NO_WINDOW)
        return ok, msg

    def _exec_appx_remove(self, action: AppxRemove) -> tuple[bool, str]:
        removed = 0
        for pkg in action.packages:
            script = (
                f"Get-AppxPackage -AllUsers '*{pkg}*' -ErrorAction SilentlyContinue | "
                "Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue; "
                f"Get-AppxPackage '*{pkg}*' -ErrorAction SilentlyContinue | "
                "Remove-AppxPackage -ErrorAction SilentlyContinue"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=45,
                creationflags=_CREATE_NO_WINDOW,
            )
            removed += 1
        return True, f"Processed AppX removal for {removed} package pattern(s)."
