"""Network, TCP/IP latency, NIC power-saving, DNS, and ping diagnostics."""

from __future__ import annotations

import re
import subprocess
import winreg
from typing import Callable

from optimasi.tweaks.models import Cmd, DnsSet, FunctionAction, RegDelete, RegSet, RiskLevel, ServiceConfig, Tweak

CATEGORY_NETWORK = "Network & DNS"
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

DNS_PRESETS = [
    ("cloudflare", "Cloudflare DNS (Fastest Gaming)", "1.1.1.1", "1.0.0.1"),
    ("google", "Google Public DNS", "8.8.8.8", "8.8.4.4"),
    ("quad9", "Quad9 Security DNS", "9.9.9.9", "149.112.112.112"),
    ("adguard", "AdGuard Ad-Blocking DNS", "94.140.14.14", "94.140.15.15"),
    ("dhcp", "Default ISP / DHCP Automatic", None, None),
]


def _toggle_nagle_all_interfaces(enable_fix: bool = True, dry_run: bool = False, log_cb: Callable[[str], None] | None = None) -> list[str]:
    base_key = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    updated = 0
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key, 0, winreg.KEY_READ) as root:
            idx = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, idx)
                    idx += 1
                except OSError:
                    break
                sub_path = f"{base_key}\\{sub}"
                if dry_run:
                    updated += 1
                    continue
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_SET_VALUE) as k:
                    if enable_fix:
                        winreg.SetValueEx(k, "TcpAckFrequency", 0, winreg.REG_DWORD, 1)
                        winreg.SetValueEx(k, "TCPNoDelay", 0, winreg.REG_DWORD, 1)
                        winreg.SetValueEx(k, "TcpDelAckTicks", 0, winreg.REG_DWORD, 0)
                    else:
                        for name in ("TcpAckFrequency", "TCPNoDelay", "TcpDelAckTicks"):
                            try:
                                winreg.DeleteValue(k, name)
                            except FileNotFoundError:
                                pass
                    updated += 1
    except OSError as exc:
        return [f"Could not access TCP/IP interfaces: {exc}"]

    if dry_run:
        return [f"[DRY-RUN] Would update Nagle settings across {updated} network interface(s)."]
    action_txt = "Disabled Nagle's Algorithm" if enable_fix else "Restored default Nagle behavior"
    return [f"{action_txt} on {updated} TCP/IP interface(s)."]


def _disable_nic_power_saving(dry_run: bool = False, log_cb: Callable[[str], None] | None = None) -> list[str]:
    nic_class = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
    zero_props = (
        "*EEE",
        "EEE",
        "AdvancedEEE",
        "EnableGreenEthernet",
        "PowerSavingMode",
        "AutoPowerSaveModeEnabled",
        "EnablePME",
        "EnableSavePowerNow",
        "EnablePowerManagement",
        "AutoDisableGigabit",
        "ReduceSpeedOnPowerDown",
        "ULPMode",
        "GigaLite",
    )
    touched_adapters = 0
    touched_values = 0
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, nic_class, 0, winreg.KEY_READ) as root:
            idx = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, idx)
                    idx += 1
                except OSError:
                    break
                if not sub.isdigit():
                    continue
                sub_path = f"{nic_class}\\{sub}"
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                        adapter_hit = False
                        for prop in zero_props:
                            try:
                                _, rtype = winreg.QueryValueEx(k, prop)
                                if not dry_run:
                                    if rtype == winreg.REG_DWORD:
                                        winreg.SetValueEx(k, prop, 0, winreg.REG_DWORD, 0)
                                    else:
                                        winreg.SetValueEx(k, prop, 0, winreg.REG_SZ, "0")
                                touched_values += 1
                                adapter_hit = True
                            except OSError:
                                continue
                        if adapter_hit:
                            touched_adapters += 1
                except OSError:
                    continue
    except OSError as exc:
        return [f"Could not inspect NIC registry keys: {exc}"]

    if dry_run:
        return [f"[DRY-RUN] Would disable {touched_values} NIC power-saving properties across {touched_adapters} adapter(s)."]
    return [f"Disabled {touched_values} NIC power-saving flags across {touched_adapters} adapter(s)."]


def ping_endpoints(targets: list[tuple[str, str]] | None = None) -> list[dict[str, str]]:
    """Run a quick 2-packet ping benchmark against DNS and SEA/Asia gaming endpoints."""
    endpoints = targets or [
        ("Cloudflare DNS", "1.1.1.1"),
        ("Google DNS", "8.8.8.8"),
        ("Quad9 Security", "9.9.9.9"),
        ("AdGuard DNS", "94.140.14.14"),
        ("Singapore (SEA Gaming)", "103.10.124.1"),
        ("Tokyo (East Asia)", "103.10.125.1"),
    ]
    results: list[dict[str, str]] = []
    for label, ip in endpoints:
        try:
            res = subprocess.run(
                ["ping", "-n", "2", "-w", "1200", ip],
                capture_output=True,
                text=True,
                timeout=6,
                creationflags=_CREATE_NO_WINDOW,
            )
            m = re.search(r"Average\s*=\s*(\d+\s*ms)", res.stdout, re.IGNORECASE)
            if not m:
                m = re.search(r"time[=<](\d+\s*ms)", res.stdout, re.IGNORECASE)
            latency = m.group(1) if m else ("Timeout" if res.returncode != 0 else "OK")
        except Exception:
            latency = "Error"
        results.append({"label": label, "ip": ip, "latency": latency})
    return results


def get_network_tweaks() -> list[Tweak]:
    tweaks = [
        Tweak(
            id="net_disable_nagle",
            name="Disable Nagle's Algorithm (TCPNoDelay & TcpAckFrequency)",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / TCP Optimizer",
            description="Sends TCP packets immediately without waiting for batching acknowledgments — lowers ping jitter in online games.",
            default_selected=True,
            tags=["network", "nagle", "ping", "latency"],
            apply_actions=[
                FunctionAction(lambda **kw: _toggle_nagle_all_interfaces(True, **kw), "Disable Nagle on all interfaces"),
            ],
            revert_actions=[
                FunctionAction(lambda **kw: _toggle_nagle_all_interfaces(False, **kw), "Restore Nagle defaults on all interfaces"),
            ],
        ),
        Tweak(
            id="net_tcp_gaming_stack",
            name="Optimize Windows TCP/IP Gaming Stack (netsh int tcp)",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / SpeedGuide",
            description="Enables RSS & TCP FastOpen, sets AutoTuning to normal, disables RSC & Timestamps, and limits MaxSynRetransmissions=2.",
            default_selected=True,
            tags=["network", "tcp", "netsh", "rss"],
            apply_actions=[
                Cmd("netsh int tcp set heuristics disabled"),
                Cmd("netsh int tcp set global rss=enabled"),
                Cmd("netsh int tcp set global rsc=disabled"),
                Cmd("netsh int tcp set global timestamps=disabled"),
                Cmd("netsh int tcp set global autotuninglevel=normal"),
                Cmd("netsh int tcp set global nonsackrttresiliency=disabled"),
                Cmd("netsh int tcp set global MaxSynRetransmissions=2"),
                Cmd("netsh int tcp set global fastopen=enabled"),
                Cmd("netsh int tcp set global fastopenfallback=enabled"),
                Cmd("netsh int tcp set global initialRto=2000"),
                Cmd("ipconfig /flushdns"),
            ],
            revert_actions=[
                Cmd("netsh int tcp set heuristics enabled"),
                Cmd("netsh int tcp set global rsc=enabled"),
                Cmd("netsh int tcp set global autotuninglevel=normal"),
                Cmd("netsh int tcp set global initialRto=3000"),
            ],
        ),
        Tweak(
            id="net_afd_buffers",
            name="Optimize AFD Socket & Network Throttling Buffers",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.MODERATE,
            source="HI+Optimizer V6",
            description="Tunes Winsock AFD FastSendDatagramThreshold, send/receive windows, and removes Windows multimedia network throttling.",
            tags=["network", "afd", "winsock", "throughput"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 0xFFFFFFFF),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "FastSendDatagramThreshold", 64000),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "DefaultSendWindow", 65536),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "DefaultReceiveWindow", 65536),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "DynamicBacklogGrowthDelta", 10),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "MaxUserPort", 65534),
                RegSet("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "TcpTimedWaitDelay", 30),
            ],
            revert_actions=[
                RegSet("HKLM", r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", 10),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "FastSendDatagramThreshold"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "DefaultSendWindow"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\AFD\Parameters", "DefaultReceiveWindow"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "MaxUserPort"),
                RegDelete("HKLM", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "TcpTimedWaitDelay"),
            ],
        ),
        Tweak(
            id="net_nic_power_saving",
            name="Disable NIC Energy Efficient Ethernet & Power Saving",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Intel & Realtek NIC Guides",
            description="Turns off *EEE, Green Ethernet, and link speed power-down on Ethernet/Wi-Fi adapters to prevent packet drops.",
            default_selected=True,
            tags=["network", "nic", "eee", "ethernet", "wifi"],
            apply_actions=[
                FunctionAction(lambda **kw: _disable_nic_power_saving(**kw), "Disable NIC power-saving flags"),
            ],
            revert_actions=[],
        ),
        Tweak(
            id="net_qos_reserve",
            name="Remove 20% Windows QoS Reserve Bandwidth Limit",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6 / Psched Policy",
            description="Sets NonBestEffortLimit to 0 so Windows Update/background tasks cannot reserve 20% of your bandwidth.",
            default_selected=True,
            tags=["network", "qos", "bandwidth"],
            apply_actions=[
                RegSet("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit", 0),
            ],
            revert_actions=[
                RegDelete("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Psched", "NonBestEffortLimit"),
            ],
        ),
        Tweak(
            id="net_wifi_fix",
            name="Fix & Enable Wi-Fi AutoConfig Service (WlanSvc)",
            category=CATEGORY_NETWORK,
            risk=RiskLevel.SAFE,
            source="HI+Optimizer V6",
            description="Ensures WlanSvc is set to Automatic and running, and flushes DNS cache.",
            tags=["wifi", "wlansvc", "fix"],
            apply_actions=[
                ServiceConfig("WlanSvc", "auto", "running"),
                Cmd("ipconfig /flushdns"),
            ],
            revert_actions=[],
        ),
    ]

    for key, label, primary, secondary in DNS_PRESETS:
        if primary is None:
            continue
        tweaks.append(
            Tweak(
                id=f"net_dns_{key}",
                name=f"Set Active Adapter DNS -> {label} ({primary})",
                category=CATEGORY_NETWORK,
                risk=RiskLevel.SAFE,
                source="Internet / DNS Performance",
                description=f"Configures all active network adapters to use {label} ({primary}, {secondary}) and flushes DNS cache.",
                tags=["dns", key, "network"],
                apply_actions=[DnsSet(primary, secondary, label)],
                revert_actions=[DnsSet(None, None, "DHCP")],
            )
        )

    return tweaks
