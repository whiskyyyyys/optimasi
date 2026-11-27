"""CPU & Power Management optimization tweaks."""

from __future__ import annotations

from optimasi.tweaks.models import Cmd, PowerCfg, PowerShell, RegDelete, RegSet, RiskLevel, ScheduledTask, ServiceConfig, Tweak

CATEGORY_CPU = "CPU & Power"


def get_cpu_tweaks() -> list[Tweak]:
    return [
        Tweak(
            id="cpu_ultimate_power",
            name="Unlock & Activate Ultimate Performance Power Plan",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="CTT WinUtil / Windows Server",
            description="Unlocks Microsoft's hidden Ultimate Performance plan to eliminate micro-latencies in CPU frequency scaling.",
            default_selected=True,
            tags=["power", "cpu", "fps", "latency"],
            apply_actions=[
                PowerShell(
                    label="Duplicate & activate Ultimate Performance power scheme",
                    script=(
                        "$guid = (powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61) "
                        "-replace '.*GUID:\\s*([0-9a-fA-F-]+).*','$1'; "
                        "if ($guid -match '^[0-9a-fA-F-]{36}$') { powercfg -setactive $guid } "
                        "else { powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c }"
                    ),
                ),
            ],
            revert_actions=[
                PowerCfg(["-setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"]),  # Balanced
            ],
        ),
        Tweak(
            id="cpu_disable_core_parking",
            name="Disable CPU Core Parking (100% Active Cores)",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer / AtlasOS",
            description="Prevents Windows from parking CPU cores on AC/DC power, reducing frame-time spikes in games and heavy workloads.",
            default_selected=True,
            tags=["cpu", "core parking", "stutter"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00\0cc5b647-c1df-4637-891a-dec35c318583", "Attributes", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00\0cc5b647-c1df-4637-891a-dec35c318583", "ValueMin", 100),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerSettings\54533251-82be-4824-96c1-47b60b740d00\0cc5b647-c1df-4637-891a-dec35c318583", "ValueMax", 100),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "100"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "100"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "10"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "5"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
        Tweak(
            id="cpu_disable_power_throttling",
            name="Disable Windows CPU Power Throttling",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer / ReviOS",
            description="Stops Windows from throttling background/foreground threads on hybrid & modern CPUs.",
            default_selected=True,
            tags=["cpu", "power", "throttling"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", 1),
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Power\PowerThrottling", "PowerThrottlingOff", 1),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", 0),
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Power\PowerThrottling", "PowerThrottlingOff"),
            ],
        ),
        Tweak(
            id="cpu_win32_priority_gaming",
            name="Optimize Foreground Thread Scheduling (Win32PrioritySeparation)",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer / Calypto Latency Guide",
            description="Sets Win32PrioritySeparation to 0x26 (38) — short, variable intervals with high foreground boost for smoother gaming & UI.",
            default_selected=True,
            tags=["cpu", "scheduler", "latency", "gaming"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 38),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 2),
            ],
        ),
        Tweak(
            id="cpu_intel_safe",
            name="Intel CPU Safe Optimization",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6",
            description="Enables Intel Processor Power Management (intelppm), sets 100% max processor state, and disables Energy Saver throttling.",
            tags=["intel", "cpu", "safe"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\intelppm", "Start", 3),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "EnergySaverState", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "EnergyEstimationEnabled", 0),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "100"]),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMIN", "100"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMIN", "5"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
        Tweak(
            id="cpu_intel_extreme",
            name="Intel CPU Extreme Low-Latency Tuning",
            category=CATEGORY_CPU,
            risk=RiskLevel.ADVANCED,
            source="HI+Optimizer V6",
            description="Disables dynamic timer tick, sets TSC sync policy enhanced, disables timer coalescing, idle maintenance tasks, and BAM overhead.",
            tags=["intel", "cpu", "extreme", "bcdedit", "latency"],
            apply_actions=[
                Cmd("bcdedit /deletevalue useplatformclock"),
                Cmd("bcdedit /set useplatformtick no"),
                Cmd("bcdedit /set disabledynamictick yes"),
                Cmd("bcdedit /set tscsyncpolicy enhanced"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "CoalescingTimerDisabled", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "GlobalTimerResolutionRequests", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "DpcWatchdogProfile", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\bam", "Start", 4),
                ScheduledTask(r"\Microsoft\Windows\TaskScheduler\Idle Maintenance", False),
                ScheduledTask(r"\Microsoft\Windows\TaskScheduler\Maintenance Configurator", False),
            ],
            revert_actions=[
                Cmd("bcdedit /deletevalue disabledynamictick"),
                Cmd("bcdedit /deletevalue useplatformtick"),
                Cmd("bcdedit /deletevalue tscsyncpolicy"),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "CoalescingTimerDisabled", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\bam", "Start", 2),
                ScheduledTask(r"\Microsoft\Windows\TaskScheduler\Idle Maintenance", True),
                ScheduledTask(r"\Microsoft\Windows\TaskScheduler\Maintenance Configurator", True),
            ],
        ),
        Tweak(
            id="cpu_amd_ryzen",
            name="AMD Ryzen CPU & CPPC Scheduler Optimization",
            category=CATEGORY_CPU,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6 / Ryzen Tuning",
            description="Tunes heterogeneous/CCX thread scheduling, disables timer coalescing, enables global timer resolution, and disables idle maintenance.",
            tags=["amd", "ryzen", "cpu", "cppc"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "CoalescingTimerDisabled", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "GlobalTimerResolutionRequests", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "SerializeTimerExpiration", 2),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "EnablePerCpuClockTickScheduling", 2),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "DynamicHeteroCpuPolicyMask", 3),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "DefaultDynamicHeteroCpuPolicy", 3),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "PowerThrottlingOff", 1),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "100"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Kernel", "CoalescingTimerDisabled", 0),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Power", "PowerThrottlingOff", 0),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "10"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
        Tweak(
            id="cpu_disable_hibernation",
            name="Disable Hibernation (Reclaim 4–16 GB SSD Space)",
            category=CATEGORY_CPU,
            risk=RiskLevel.MODERATE,
            source="CTT WinUtil / HI+Optimizer",
            description="Deletes hiberfil.sys and disables Fast Startup/Hibernate. Recommended for desktops and SSD systems (skip if you rely on laptop Hibernate).",
            tags=["power", "ssd", "hibernation", "storage"],
            apply_actions=[
                PowerCfg(["-h", "off"]),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", 0),
            ],
            revert_actions=[
                PowerCfg(["-h", "on"]),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled", 1),
            ],
        ),
        Tweak(
            id="cpu_usb_pcie_power",
            name="Disable USB Selective Suspend & PCIe Link Power Saving",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Audio & Mouse Latency",
            description="Prevents USB gaming mice, keyboards, and PCIe devices from entering low-power sleep states.",
            default_selected=True,
            tags=["usb", "pcie", "mouse", "latency"],
            apply_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\USB", "DisableSelectiveSuspend", 1),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\HidUsb", "IdleEnabled", 0),
                PowerCfg(["/SETACVALUEINDEX", "SCHEME_CURRENT", "2a737441-1930-4402-8d77-b2beb1463538", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "0"]),
                PowerCfg(["/SETACVALUEINDEX", "SCHEME_CURRENT", "501a4d13-42af-4429-9fd1-a8218c268e20", "ee12f906-d277-404b-b6da-e5fa1a576df5", "0"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\USB", "DisableSelectiveSuspend", 0),
                PowerCfg(["/SETACVALUEINDEX", "SCHEME_CURRENT", "2a737441-1930-4402-8d77-b2beb1463538", "48e6b7a6-50f5-4782-a5d4-53bb8f07e226", "1"]),
                PowerCfg(["/SETACVALUEINDEX", "SCHEME_CURRENT", "501a4d13-42af-4429-9fd1-a8218c268e20", "ee12f906-d277-404b-b6da-e5fa1a576df5", "2"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
        Tweak(
            id="cpu_laptop_ac_dc_smart",
            name="Smart Laptop AC/DC Power Profile (Full Plugged-In, Cool Battery)",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="Laptop Ryzen/Intel AC-DC Guide",
            description="Sets 100% CPU & unparked cores when plugged into AC charger, and caps DC battery CPU at 80% + core parking for longer battery life.",
            default_selected=True,
            tags=["laptop", "battery", "ac", "dc", "ryzen"],
            apply_actions=[
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "100"]),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "100"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "80"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "10"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "100"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
        Tweak(
            id="cpu_laptop_cool_silent",
            name="Laptop Cool & Quiet Mode (Disable Hot Turbo Spikes)",
            category=CATEGORY_CPU,
            risk=RiskLevel.SAFE,
            source="Laptop Thermal & Fan Control",
            description="Caps AC processor state at 99% (disables aggressive turbo spikes) and DC at 80%, lowering laptop heat and fan noise significantly.",
            tags=["laptop", "cool", "quiet", "thermal", "fan"],
            apply_actions=[
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "99"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "80"]),
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "50"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "CPMINCORES", "10"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
            revert_actions=[
                PowerCfg(["-setacvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "100"]),
                PowerCfg(["-setdcvalueindex", "scheme_current", "sub_processor", "PROCTHROTTLEMAX", "100"]),
                PowerCfg(["-setactive", "scheme_current"]),
            ],
        ),
    ]
