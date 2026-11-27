"""RAM, Kernel Memory Management, and NTFS/SSD Storage optimization tweaks."""

from __future__ import annotations

import winreg
from typing import Callable

import psutil

from optimasi.tweaks.models import Cmd, FunctionAction, PowerShell, RegDelete, RegSet, RiskLevel, Tweak

CATEGORY_RAM = "RAM & Storage"


def _tune_svchost_split(dry_run: bool = False, log_cb: Callable[[str], None] | None = None) -> list[str]:
    """Set SvcHostSplitThresholdInKB dynamically based on total physical RAM."""
    total_kb = int(psutil.virtual_memory().total // 1024)
    # Round up slightly above total RAM KB as recommended for systems >= 4GB RAM
    target_kb = max(3670016, total_kb)
    if dry_run:
        return [f"[DRY-RUN] Would set SvcHostSplitThresholdInKB = {target_kb} (matched to {round(total_kb / 1048576, 1)} GB RAM)"]

    with winreg.CreateKeyEx(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, "SvcHostSplitThresholdInKB", 0, winreg.REG_DWORD, target_kb)
    return [f"Set SvcHostSplitThresholdInKB = {target_kb} KB (reduces svchost.exe process clutter)."]


def get_ram_storage_tweaks() -> list[Tweak]:
    return [
        Tweak(
            id="ram_svchost_auto",
            name="Auto-Tune SvcHostSplitThresholdInKB to Installed RAM",
            category=CATEGORY_RAM,
            risk=RiskLevel.SAFE,
            source="CTT WinUtil / HI+Optimizer V6",
            description="Consolidates svchost.exe service hosts proportionally to your physical RAM, cutting dozens of redundant background processes.",
            default_selected=True,
            tags=["ram", "svchost", "processes"],
            apply_actions=[
                FunctionAction(_tune_svchost_split, "Calculate & apply SvcHostSplitThresholdInKB"),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control", "SvcHostSplitThresholdInKB", 3670016),
            ],
        ),
        Tweak(
            id="ram_kernel_paging",
            name="Keep Kernel & Drivers in RAM (DisablePagingExecutive)",
            category=CATEGORY_RAM,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Sysinternals",
            description="Prevents Windows kernel and drivers from paging out to disk (recommended on 8 GB+ RAM) and skips zeroing pagefile on shutdown.",
            default_selected=True,
            tags=["ram", "kernel", "paging", "shutdown"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "DisablePagingExecutive", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "ClearPageFileAtShutdown", 0),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer", "AlwaysUnloadDll", 1),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management", "DisablePagingExecutive", 0),
                RegDelete("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer", "AlwaysUnloadDll"),
            ],
        ),
        Tweak(
            id="ram_disable_compression",
            name="Disable Windows Memory Compression (Lower CPU Overhead)",
            category=CATEGORY_RAM,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6 / AtlasOS",
            description="Disables MMAgent memory compression to eliminate background CPU compression spikes on 16 GB+ RAM gaming PCs.",
            tags=["ram", "compression", "cpu", "gaming"],
            apply_actions=[
                PowerShell("Disable-MMAgent -MemoryCompression", label="Disable Memory Compression"),
            ],
            revert_actions=[
                PowerShell("Enable-MMAgent -MemoryCompression", label="Re-enable Memory Compression"),
            ],
        ),
        Tweak(
            id="storage_ntfs_perf",
            name="NTFS & SSD Performance Tweaks (LastAccess, 8dot3, LongPaths)",
            category=CATEGORY_RAM,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Microsoft fsutil",
            description="Disables NTFS last-access timestamp writes & legacy 8.3 short names, raises NtfsMemoryUsage=2, and enables Win32 LongPaths.",
            default_selected=True,
            tags=["ssd", "ntfs", "storage", "io"],
            apply_actions=[
                Cmd("fsutil behavior set disablelastaccess 1"),
                Cmd("fsutil behavior set disable8dot3 1"),
                Cmd("fsutil behavior set memoryusage 2"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsMemoryUsage", 2),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsDisableLastAccessUpdate", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "LongPathsEnabled", 1),
            ],
            revert_actions=[
                Cmd("fsutil behavior set disablelastaccess 0"),
                Cmd("fsutil behavior set disable8dot3 0"),
                Cmd("fsutil behavior set memoryusage 1"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\FileSystem", "NtfsMemoryUsage", 1),
            ],
        ),
        Tweak(
            id="storage_disable_delivery_opt",
            name="Disable Windows Update P2P Delivery Optimization",
            category=CATEGORY_RAM,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Win11Debloat",
            description="Stops Windows from using your disk I/O and upload bandwidth to seed updates to other PCs on the internet.",
            default_selected=True,
            tags=["storage", "bandwidth", "windows update"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode", 0),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config", "DODownloadMode", 0),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization", "DODownloadMode"),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config", "DODownloadMode", 1),
            ],
        ),
    ]
