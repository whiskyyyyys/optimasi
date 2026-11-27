"""Windows hardware, OS, GPU vendor, and runtime telemetry snapshot."""

from __future__ import annotations

import platform
import subprocess
import sys
import winreg
from typing import Any

import psutil

from optimasi.core.admin import is_admin, is_compiled

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


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


def get_system_snapshot() -> dict[str, Any]:
    """Collect a comprehensive, fast snapshot of system hardware & runtime state."""
    os_info = get_os_info()
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    gpus = detect_gpus()
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
        "cpu": {
            "name": cpu_name,
            "vendor": cpu_vendor,
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_cores": psutil.cpu_count(logical=True) or 1,
            "usage_percent": psutil.cpu_percent(interval=0.1),
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
