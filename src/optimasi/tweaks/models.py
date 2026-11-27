"""Dataclass models for Optimization Actions, Tweaks, and Presets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class RiskLevel(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    ADVANCED = "ADVANCED"


class Action:
    """Base class for an atomic system optimization action."""

    def describe(self) -> str:
        raise NotImplementedError


@dataclass(slots=True)
class RegSet(Action):
    hive: str  # "HKLM", "HKCU", "HKCR"
    subkey: str
    name: str
    value: Any
    reg_type: str = "REG_DWORD"  # REG_DWORD, REG_SZ, REG_QWORD, REG_BINARY, REG_EXPAND_SZ

    def describe(self) -> str:
        val_name = self.name if self.name else "(Default)"
        return f"REG SET {self.hive}\\{self.subkey} [{val_name}] = {self.value} ({self.reg_type})"


@dataclass(slots=True)
class RegDelete(Action):
    hive: str
    subkey: str
    name: str | None = None  # None deletes entire subkey

    def describe(self) -> str:
        if self.name is None:
            return f"REG DELETE KEY {self.hive}\\{self.subkey}"
        return f"REG DELETE {self.hive}\\{self.subkey} [{self.name}]"


@dataclass(slots=True)
class ServiceConfig(Action):
    service_name: str
    start_type: str  # "auto", "delayed-auto", "demand", "disabled"
    state: str | None = None  # "running", "stopped", None

    def describe(self) -> str:
        extra = f" -> {self.state}" if self.state else ""
        return f"SERVICE {self.service_name} start={self.start_type}{extra}"


@dataclass(slots=True)
class PowerCfg(Action):
    args: list[str]

    def describe(self) -> str:
        return f"powercfg {' '.join(self.args)}"


@dataclass(slots=True)
class Cmd(Action):
    command: str | list[str]
    shell: bool = True
    ignore_errors: bool = True

    def describe(self) -> str:
        cmd_str = self.command if isinstance(self.command, str) else " ".join(self.command)
        return f"CMD: {cmd_str}"


@dataclass(slots=True)
class PowerShell(Action):
    script: str
    label: str = ""
    ignore_errors: bool = True

    def describe(self) -> str:
        return self.label or f"PowerShell: {self.script[:80]}..."


@dataclass(slots=True)
class ScheduledTask(Action):
    task_path: str
    enabled: bool

    def describe(self) -> str:
        state = "ENABLE" if self.enabled else "DISABLE"
        return f"TASK {state}: {self.task_path}"


@dataclass(slots=True)
class HostsBlock(Action):
    domains: list[str]
    enable: bool = True

    def describe(self) -> str:
        mode = f"BLOCK {len(self.domains)} domains" if self.enable else "UNBLOCK telemetry domains"
        return f"HOSTS: {mode}"


@dataclass(slots=True)
class DnsSet(Action):
    primary: str | None  # None resets to DHCP
    secondary: str | None = None
    label: str = ""

    def describe(self) -> str:
        if self.primary is None:
            return "DNS: Reset active adapters to DHCP"
        return f"DNS: Set {self.label or 'Custom'} ({self.primary}, {self.secondary or '-'})"


@dataclass(slots=True)
class AppxRemove(Action):
    packages: list[str]

    def describe(self) -> str:
        return f"APPX REMOVE: {', '.join(self.packages)}"


@dataclass(slots=True)
class FunctionAction(Action):
    fn: Callable[..., list[str]]
    label: str

    def describe(self) -> str:
        return f"CUSTOM: {self.label}"


@dataclass(slots=True)
class Tweak:
    id: str
    name: str
    category: str
    risk: RiskLevel
    description: str
    source: str
    apply_actions: list[Action] = field(default_factory=list)
    revert_actions: list[Action] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    default_selected: bool = False

    @property
    def reversible(self) -> bool:
        return len(self.revert_actions) > 0


@dataclass(slots=True)
class Preset:
    id: str
    name: str
    description: str
    tweak_ids: list[str]
    badge: str = ""
