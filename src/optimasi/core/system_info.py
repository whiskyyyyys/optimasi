"""Windows hardware, laptop chassis/battery, process monitor, and runtime telemetry."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import winreg
from typing import Any

import psutil

from optimasi.core.admin import is_admin, is_compiled

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

_PROTECTED_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "lsm.exe",
    "svchost.exe",
    "winlogon.exe",
    "explorer.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "audiodg.exe",
}


def _read_reg_str(root: int, subkey: str, value_name: str, default: str = "") -> str:
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, value_name)
            return str(val).strip()
    except OSError:
        return default


def get_os_info() -> dict[str, str]:
    """Return friendly Windows OS name, release, and build number."""
    nt_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    product = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, nt_key, "ProductName", platform.system())
    display_ver = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, nt_key, "DisplayVersion", "")
    build_str = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, nt_key, "CurrentBuildNumber", platform.version())
    ubr = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, nt_key, "UBR", "")

    try:
        if int(build_str) >= 22000 and "Windows 10" in product:
            product = product.replace("Windows 10", "Windows 11")
    except ValueError:
        pass

    full_build = f"{build_str}.{ubr}" if ubr else build_str
    return {
        "name": product,
        "display_version": display_ver or platform.release(),
        "build": full_build,
        "arch": platform.machine(),
    }


def get_cpu_name() -> str:
    """Return CPU brand string from registry."""
    name = _read_reg_str(
        winreg.HKEY_LOCAL_MACHINE,
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        "ProcessorNameString",
        "",
    )
    if name:
        return " ".join(name.split())
    return platform.processor() or "Unknown CPU"


def get_chassis_info() -> dict[str, Any]:
    """Detect device manufacturer, model, and battery/laptop status."""
    bios_key = r"HARDWARE\DESCRIPTION\System\BIOS"
    manufacturer = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, bios_key, "SystemManufacturer", "Unknown")
    model = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, bios_key, "SystemProductName", "PC")

    bat = None
    try:
        bat = psutil.sensors_battery()
    except Exception:
        bat = None

    has_battery = bat is not None
    return {
        "manufacturer": manufacturer,
        "model": model,
        "is_laptop": has_battery,
        "battery": {
            "has_battery": has_battery,
            "percent": int(round(bat.percent)) if bat else None,
            "plugged": bool(bat.power_plugged) if bat else True,
            "secs_left": int(bat.secsleft) if (bat and isinstance(bat.secsleft, (int, float)) and bat.secsleft >= 0) else None,
        },
    }


def detect_gpus() -> list[dict[str, str]]:
    """Detect installed display adapters from Windows registry."""
    gpus: list[dict[str, str]] = []
    class_key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_key_path, 0, winreg.KEY_READ) as root:
            idx = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(root, idx)
                    idx += 1
                except OSError:
                    break
                if not sub_name.isdigit():
                    continue
                sub_path = f"{class_key_path}\\{sub_name}"
                desc = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, sub_path, "DriverDesc")
                if not desc:
                    desc = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, sub_path, "HardwareInformation.AdapterString")
                provider = _read_reg_str(winreg.HKEY_LOCAL_MACHINE, sub_path, "ProviderName")
                if not desc:
                    continue
                upper = f"{desc} {provider}".upper()
                if "NVIDIA" in upper:
                    vendor = "NVIDIA"
                elif "AMD" in upper or "RADEON" in upper or "ATI " in upper:
                    vendor = "AMD"
                elif "INTEL" in upper:
                    vendor = "INTEL"
                else:
                    vendor = "OTHER"
                gpus.append({"name": desc, "vendor": vendor, "subkey": sub_name})
    except OSError:
        pass
    return gpus


def get_active_power_plan() -> str:
    """Return active Windows power plan name."""
    try:
        res = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_CREATE_NO_WINDOW,
        )
        out = (res.stdout or "").strip()
        if "(" in out and ")" in out:
            return out[out.rfind("(") + 1 : out.rfind(")")].strip()
        return out or "Unknown"
    except Exception:
        return "Unknown"


def get_net_io_counters() -> tuple[int, int]:
    """Return cumulative (bytes_recv, bytes_sent) across NICs."""
    try:
        io = psutil.net_io_counters()
        return int(io.bytes_recv), int(io.bytes_sent)
    except Exception:
        return 0, 0


def get_top_processes(limit: int = 18) -> list[dict[str, Any]]:
    """Return top running processes sorted by memory consumption."""
    rows: list[dict[str, Any]] = []
    own_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
        try:
            pid = int(proc.info["pid"])
            if pid <= 4 or pid == own_pid:
                continue
            name = proc.info.get("name") or f"PID {pid}"
            mem = proc.info.get("memory_info")
            ram_mb = round((mem.rss / (1024 * 1024)) if mem else 0.0, 1)
            cpu = round(float(proc.info.get("cpu_percent") or 0.0), 1)
            rows.append(
                {
                    "pid": pid,
                    "name": name,
                    "ram_mb": ram_mb,
                    "cpu_percent": cpu,
                    "protected": name.lower() in _PROTECTED_PROCESSES,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    rows.sort(key=lambda r: r["ram_mb"], reverse=True)
    return rows[:limit]


def terminate_process(pid: int, dry_run: bool = False) -> tuple[bool, str]:
    """Safely terminate a non-critical user/background process."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except psutil.NoSuchProcess:
        return False, f"Process PID {pid} no longer exists."
    except psutil.AccessDenied:
        return False, f"Access denied for PID {pid}."

    if name.lower() in _PROTECTED_PROCESSES or pid <= 4 or pid == os.getpid():
        return False, f"Refused to terminate protected process: {name} (PID {pid})."

    if dry_run:
        return True, f"[DRY-RUN] Would terminate process {name} (PID {pid})."

    try:
        proc.terminate()
        proc.wait(timeout=3)
        return True, f"Terminated {name} (PID {pid})."
    except psutil.TimeoutExpired:
        try:
            proc.kill()
            return True, f"Force-killed {name} (PID {pid})."
        except Exception as exc:
            return False, f"Could not kill {name}: {exc}"
    except Exception as exc:
        return False, f"Failed to terminate {name}: {exc}"


def get_system_snapshot(fast: bool = False) -> dict[str, Any]:
    """Collect a comprehensive snapshot of system hardware, chassis & runtime state."""
    os_info = get_os_info()
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    gpus = detect_gpus()
    chassis = get_chassis_info()

    primary_vendor = "UNKNOWN"
    for gpu in gpus:
        if gpu["vendor"] in ("NVIDIA", "AMD", "INTEL"):
            primary_vendor = gpu["vendor"]
            if gpu["vendor"] in ("NVIDIA", "AMD"):
                break

    cpu_name = get_cpu_name()
    cpu_vendor = "UNKNOWN"
    if "INTEL" in cpu_name.upper():
        cpu_vendor = "INTEL"
    elif "AMD" in cpu_name.upper() or "RYZEN" in cpu_name.upper():
        cpu_vendor = "AMD"

    return {
        "os": os_info,
        "manufacturer": chassis["manufacturer"],
        "model": chassis["model"],
        "is_laptop": chassis["is_laptop"],
        "battery": chassis["battery"],
        "cpu": {
            "name": cpu_name,
            "vendor": cpu_vendor,
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_cores": psutil.cpu_count(logical=True) or 1,
            "usage_percent": psutil.cpu_percent(interval=None if fast else 0.08),
        },
        "ram": {
            "total_gb": round(vm.total / (1024**3), 2),
            "used_gb": round(vm.used / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "percent": vm.percent,
            "total_kb": int(vm.total // 1024),
        },
        "disk_c": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk.percent,
        },
        "gpus": gpus,
        "gpu_primary_vendor": primary_vendor,
        "power_plan": get_active_power_plan(),
        "is_admin": is_admin(),
        "is_compiled": is_compiled(),
        "python_version": platform.python_version(),
        "executable": sys.executable,
    }
