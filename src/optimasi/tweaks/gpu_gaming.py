"""GPU, DirectX, GameDVR, MMCSS, and Auto-Game Priority tweaks."""

from __future__ import annotations

import os
import winreg
from pathlib import Path
from typing import Callable

from optimasi.tweaks.models import Cmd, FunctionAction, PowerCfg, PowerShell, RegDelete, RegSet, RiskLevel, Tweak

CATEGORY_GPU = "GPU & Gaming"


def _discover_installed_game_exes() -> list[str]:
    """Scan common Steam, Epic, Riot, Roblox, Battle.net, and EA install paths."""
    user = os.environ.get("USERPROFILE", str(Path.home()))
    candidates = [
        r"C:\Program Files\Epic Games\Fortnite\FortniteGame\Binaries\Win64\FortniteClient-Win64-Shipping.exe",
        r"C:\Program Files\Epic Games\RocketLeague\Binaries\Win64\RocketLeague.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Tom Clancy's Rainbow Six Siege\RainbowSix.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Overwatch\Overwatch.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Apex Legends\r5apex.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V\GTA5.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\VRChat\VRChat.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Dead by Daylight\DeadByDaylight\Binaries\Win64\DeadByDaylight-Win64-Shipping.exe",
        r"C:\Program Files (x86)\Steam\steamapps\common\Aimlabs\AimLab_tb.exe",
        r"C:\Riot Games\VALORANT\live\VALORANT.exe",
        r"C:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe",
        r"C:\Program Files\Genshin Impact\Genshin Impact Game\GenshinImpact.exe",
        str(Path(user) / "AppData" / "Local" / "osu!" / "osu!.exe"),
    ]
    for base in [
        Path(r"C:\Program Files (x86)\Roblox\Versions"),
        Path(user) / "AppData" / "Local" / "Roblox" / "Versions",
    ]:
        if base.exists():
            for ver in sorted(base.glob("version-*"), reverse=True):
                exe = ver / "RobloxPlayerBeta.exe"
                if exe.exists():
                    candidates.append(str(exe))
                    break

    return [p for p in dict.fromkeys(candidates) if Path(p).exists()]


def _auto_boost_games(dry_run: bool = False, log_cb: Callable[[str], None] | None = None) -> list[str]:
    found = _discover_installed_game_exes()
    if not found:
        return ["No common game executables detected in default paths (nothing changed)."]
    if dry_run:
        return [f"Detected {len(found)} game(s); would apply High Performance GPU + High CPU Priority."]

    gpu_pref_key = r"Software\Microsoft\DirectX\UserGpuPreferences"
    layers_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
    for exe_path in found:
        exe_name = Path(exe_path).name
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, gpu_pref_key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, exe_path, 0, winreg.REG_SZ, "GpuPreference=2;")
        with winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{exe_name}\PerfOptions",
            0,
            winreg.KEY_SET_VALUE,
        ) as k:
            winreg.SetValueEx(k, "CpuPriorityClass", 0, winreg.REG_DWORD, 3)
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, layers_key, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, exe_path, 0, winreg.REG_SZ, "~ DISABLEDXMAXIMIZEDWINDOWEDMODE HIGHDPIAWARE")
    return [f"Boosted {len(found)} detected game(s) with High-Perf GPU & CPU Priority."]


def _enable_gpu_msi_mode(dry_run: bool = False, log_cb: Callable[[str], None] | None = None) -> list[str]:
    """Enable Message Signaled Interrupts (MSI) on PCIe Display Adapters."""
    pci_root = r"SYSTEM\CurrentControlSet\Enum\PCI"
    gpu_class = "{4d36e968-e325-11ce-bfc1-08002be10318}"
    targets: list[tuple[str, str]] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, pci_root, 0, winreg.KEY_READ) as pci:
            i = 0
            while True:
                try:
                    dev_id = winreg.EnumKey(pci, i)
                    i += 1
                except OSError:
                    break
                dev_path = f"{pci_root}\\{dev_id}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, dev_path, 0, winreg.KEY_READ) as dev:
                    j = 0
                    while True:
                        try:
                            inst_id = winreg.EnumKey(dev, j)
                            j += 1
                        except OSError:
                            break
                        inst_path = f"{dev_path}\\{inst_id}"
                        try:
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, inst_path, 0, winreg.KEY_READ) as inst:
                                cguid, _ = winreg.QueryValueEx(inst, "ClassGUID")
                                desc, _ = winreg.QueryValueEx(inst, "DeviceDesc")
                                if str(cguid).lower() == gpu_class:
                                    targets.append((inst_path, str(desc).split(";")[-1]))
                        except OSError:
                            continue
    except OSError:
        return ["Could not enumerate PCI display adapters."]

    if not targets:
        return ["No PCIe display adapter found for MSI mode."]
    if dry_run:
        return [f"Would enable MSI Mode on {len(targets)} GPU(s): {', '.join(d for _, d in targets)}"]

    updated = 0
    for inst_path, desc in targets:
        msi_path = f"{inst_path}\\Device Parameters\\Interrupt Management\\MessageSignaledInterruptProperties"
        try:
            with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, msi_path, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "MSISupported", 0, winreg.REG_DWORD, 1)
            updated += 1
        except OSError:
            continue
    return [f"Enabled MSI Mode on {updated}/{len(targets)} GPU device(s) (reboot to apply)."]


def get_gpu_tweaks() -> list[Tweak]:
    return [
        Tweak(
            id="gpu_hags_enable",
            name="Enable Hardware-Accelerated GPU Scheduling (HAGS) & TDR Guard",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Windows 11",
            description="Offloads GPU scheduling to dedicated GPU hardware and increases TdrDelay to 10s to prevent driver reset crashes.",
            default_selected=True,
            tags=["gpu", "hags", "directx", "tdr"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 2),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDelay", 10),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", 1),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "TdrDelay"),
            ],
        ),
        Tweak(
            id="gpu_windowed_optimizations",
            name="Enable Windowed Game Optimizations & DirectFlip",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Microsoft DirectX",
            description="Enables Flip Model / SwapEffectUpgradeEnable for lower input lag in borderless windowed games.",
            default_selected=True,
            tags=["gpu", "directx", "flip", "borderless"],
            apply_actions=[
                RegSet("HKCU", r"Software\Microsoft\DirectX\UserGpuPreferences", "DirectXUserGlobalSettings", "SwapEffectUpgradeEnable=1;", "REG_SZ"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "ForceDirectFlip", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "PlatformSupportMiracast", 0),
            ],
            revert_actions=[
                RegDelete("HKCU", r"Software\Microsoft\DirectX\UserGpuPreferences", "DirectXUserGlobalSettings"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "ForceDirectFlip"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "PlatformSupportMiracast", 1),
            ],
        ),
        Tweak(
            id="gpu_disable_gamedvr",
            name="Disable GameDVR & Background Xbox Recording",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / CTT WinUtil",
            description="Stops background screen capture hooks that steal GPU VRAM and cause frame pacing micro-stutters.",
            default_selected=True,
            tags=["gamedvr", "xbox", "fps", "stutter"],
            apply_actions=[
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 0),
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_FSEBehaviorMode", 2),
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", 1),
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", 1),
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_EFSEFeatureFlags", 0),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", 0),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AudioCaptureEnabled", 0),
            ],
            revert_actions=[
                RegSet("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", 1),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR"),
                RegSet("HKCU", r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 1),
            ],
        ),
        Tweak(
            id="gpu_mmcss_gaming",
            name="MMCSS Multimedia & Game Thread Priority Boost",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / TCP Optimizer",
            description="Prioritizes Multimedia Class Scheduler Service (Games task) GPU/CPU priority and disables NetworkThrottlingIndex.",
            default_selected=True,
            tags=["mmcss", "gaming", "priority", "fps"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", 10),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 0xFFFFFFFF),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NoLazyMode", 1),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", 8),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", 6),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "High", "REG_SZ"),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", "High", "REG_SZ"),
            ],
            revert_actions=[
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", 20),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 10),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", 8),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", 2),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "Medium", "REG_SZ"),
            ],
        ),
        Tweak(
            id="gpu_nvidia_safe",
            name="NVIDIA GPU Safe Optimization & Telemetry Removal",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6",
            description="Disables NVIDIA telemetry tasks, raises nvlddmkm & DXGKrnl thread priority, and enables per-CPU core DPC.",
            tags=["nvidia", "gpu", "telemetry", "safe"],
            apply_actions=[
                PowerCfg(["/setacvalueindex", "SCHEME_CURRENT", "SUB_GRAPHICS", "GPUPREFERENCE", "1"]),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\Parameters", "ThreadPriority", 31),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\DXGKrnl\Parameters", "ThreadPriority", 15),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "RmGpsPsEnablePerCpuCoreDpc", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm", "RmGpsPsEnablePerCpuCoreDpc", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableRID61684", 1),
                Cmd("schtasks /Change /TN \"\\NvTmRep_CrashReport1_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8}\" /Disable"),
                Cmd("schtasks /Change /TN \"\\NvTmRep_CrashReport2_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8}\" /Disable"),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\Parameters", "ThreadPriority"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\DXGKrnl\Parameters", "ThreadPriority"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "RmGpsPsEnablePerCpuCoreDpc"),
            ],
        ),
        Tweak(
            id="gpu_nvidia_aggressive",
            name="NVIDIA GPU Extreme Latency Tweaks (Disable Preemption)",
            category=CATEGORY_GPU,
            risk=RiskLevel.ADVANCED,
            source="HI+Optimizer V6",
            description="Disables NVIDIA GPU/Compute/Mid-Buffer preemption and sets Direct3D MaxLoaderThreads=10 for lowest latency.",
            tags=["nvidia", "gpu", "extreme", "preemption"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableGfxPreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableComputePreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnablePreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "GPUPreemptionLevel", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "ComputePreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableMidGfxPreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableMidBufferPreemption", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "DisablePreemption", 1),
                RegSet("HKLM", r"SOFTWARE\Microsoft\Direct3D", "MaxLoaderThreads", 10),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableGfxPreemption"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnableComputePreemption"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\nvlddmkm\FTS", "EnablePreemption"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "DisablePreemption"),
            ],
        ),
        Tweak(
            id="gpu_amd_radeon",
            name="AMD Radeon GPU Optimization (Disable ULPS & StutterMode)",
            category=CATEGORY_GPU,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6",
            description="Disables AMD Ultra Low Power State (ULPS), StutterMode, enables ReBar support, and silences Adrenalin web/toast bloat.",
            tags=["amd", "radeon", "gpu", "ulps"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "EnableUlps", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "Ulps", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000\UMD", "StutterMode", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\amdkmdag", "EnableUlps", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\amdkmdag", "PP_PhmUseDummyBackEnd", 0),
                RegSet("HKCU", r"Software\AMD\CN", "AllowWebContent", "false", "REG_SZ"),
                RegSet("HKCU", r"Software\AMD\CN", "CN_Hide_Toast_Notification", "true", "REG_SZ"),
                RegSet("HKCU", r"Software\AMD\CN", "AnimationEffect", "false", "REG_SZ"),
                RegSet("HKCU", r"Software\AMD\CN", "AutoUpdate", 0),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "EnableUlps", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\amdkmdag", "EnableUlps", 1),
                RegSet("HKCU", r"Software\AMD\CN", "AnimationEffect", "true", "REG_SZ"),
            ],
        ),
        Tweak(
            id="gpu_intel_arc",
            name="Intel UHD/Iris/Arc GPU Optimization",
            category=CATEGORY_GPU,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6",
            description="Sets Intel GMM DedicatedSegmentSize=1024, disables GPU power PM states, and reduces DWM MaxQueuedBuffers to 2.",
            tags=["intel", "gpu", "igpu", "arc"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Intel\GMM", "DedicatedSegmentSize", 1024),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "PowerSettingEnable", 0),
                RegSet("HKCU", r"Software\Microsoft\Windows\DWM", "MaxQueuedBuffers", 2),
                RegSet("HKCU", r"Software\Microsoft\Windows\DWM", "UseMachineCheck", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000", "PowerPMstates", 0),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Intel\GMM", "DedicatedSegmentSize"),
                RegDelete("HKCU", r"Software\Microsoft\Windows\DWM", "MaxQueuedBuffers"),
            ],
        ),
        Tweak(
            id="gpu_auto_game_boost",
            name="Auto-Detect Installed Games -> High-Perf GPU & CPU Priority",
            category=CATEGORY_GPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 (Enhanced)",
            description="Scans Steam, Epic, Riot, Roblox & osu! paths and forces High-Performance GPU + High CPU Priority + Fullscreen Optimization flags.",
            default_selected=True,
            tags=["games", "gpu", "priority", "auto"],
            apply_actions=[
                FunctionAction(_auto_boost_games, "Auto-detect & prioritize installed games"),
            ],
            revert_actions=[],
        ),
        Tweak(
            id="gpu_msi_mode",
            name="Enable MSI (Message Signaled Interrupts) Mode on GPU",
            category=CATEGORY_GPU,
            risk=RiskLevel.ADVANCED,
            source="MSI Utility / AtlasOS",
            description="Switches PCIe display adapter interrupts from legacy IRQ line-based to low-latency MSI mode (requires reboot).",
            tags=["gpu", "msi", "interrupts", "latency"],
            apply_actions=[
                FunctionAction(_enable_gpu_msi_mode, "Enable MSI Mode for PCIe GPUs"),
            ],
            revert_actions=[],
        ),
        Tweak(
            id="gpu_disable_vbs",
            name="Disable VBS & Memory Integrity (Core Isolation) for Gaming FPS",
            category=CATEGORY_GPU,
            risk=RiskLevel.ADVANCED,
            source="HI+Optimizer V6 / Microsoft Gaming Guide",
            description="Disables Virtualization-Based Security (VBS) & HVCI, often giving 5–15% higher FPS. Trade-off: reduces kernel isolation security.",
            tags=["vbs", "hvci", "fps", "security"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\DeviceGuard", "EnableVirtualizationBasedSecurity", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity", "Enabled", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\CI\Policy", "VerifiedAndReputablePolicyState", 0),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\DeviceGuard", "EnableVirtualizationBasedSecurity", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity", "Enabled", 1),
            ],
        ),
    ]
