"""Aggregated Windows optimization tweaks catalog and one-click presets."""

from __future__ import annotations

from optimasi.tweaks.cpu_power import CATEGORY_CPU, get_cpu_tweaks
from optimasi.tweaks.gpu_gaming import CATEGORY_GPU, get_gpu_tweaks
from optimasi.tweaks.models import Preset, Tweak
from optimasi.tweaks.network_dns import CATEGORY_NETWORK, get_network_tweaks
from optimasi.tweaks.privacy_debloat import CATEGORY_PRIVACY, get_privacy_tweaks
from optimasi.tweaks.ram_storage import CATEGORY_RAM, get_ram_storage_tweaks
from optimasi.tweaks.services_system import CATEGORY_SERVICES, get_services_system_tweaks

CATEGORIES = [
    CATEGORY_CPU,
    CATEGORY_GPU,
    CATEGORY_NETWORK,
    CATEGORY_PRIVACY,
    CATEGORY_RAM,
    CATEGORY_SERVICES,
]

ALL_TWEAKS: list[Tweak] = (
    get_cpu_tweaks()
    + get_gpu_tweaks()
    + get_network_tweaks()
    + get_privacy_tweaks()
    + get_ram_storage_tweaks()
    + get_services_system_tweaks()
)

TWEAK_BY_ID: dict[str, Tweak] = {t.id: t for t in ALL_TWEAKS}

PRESETS: list[Preset] = [
    Preset(
        id="safe_daily",
        name="Safe Daily Driver",
        badge="RECOMMENDED",
        description="Safe privacy, AI/Edge debloat, NTFS/RAM polish, telemetry cleanup, and snappy UI with zero risky changes.",
        tweak_ids=[
            "cpu_disable_power_throttling",
            "cpu_usb_pcie_power",
            "gpu_disable_gamedvr",
            "net_qos_reserve",
            "priv_telemetry_diag",
            "priv_disable_ai_copilot",
            "priv_debloat_edge",
            "priv_ads_spotlight",
            "priv_telemetry_tasks",
            "ram_svchost_auto",
            "ram_kernel_paging",
            "storage_ntfs_perf",
            "storage_disable_delivery_opt",
            "sys_classic_context_menu",
            "sys_explorer_power_user",
            "sys_disable_bing_widgets",
            "svc_disable_non_essential",
        ],
    ),
    Preset(
        id="gaming_pro",
        name="Gaming & Low Latency Pro",
        badge="FPS + PING",
        description="Safe Daily tweaks + Ultimate Performance power, unparked CPU cores, HAGS, MMCSS Gaming, Nagle/TCP fix, Raw Mouse & Auto-Game Boost.",
        tweak_ids=[
            "cpu_ultimate_power",
            "cpu_disable_core_parking",
            "cpu_disable_power_throttling",
            "cpu_win32_priority_gaming",
            "cpu_usb_pcie_power",
            "gpu_hags_enable",
            "gpu_windowed_optimizations",
            "gpu_disable_gamedvr",
            "gpu_mmcss_gaming",
            "gpu_auto_game_boost",
            "net_disable_nagle",
            "net_tcp_gaming_stack",
            "net_nic_power_saving",
            "net_qos_reserve",
            "priv_telemetry_diag",
            "priv_disable_ai_copilot",
            "priv_debloat_edge",
            "priv_ads_spotlight",
            "priv_telemetry_tasks",
            "ram_svchost_auto",
            "ram_kernel_paging",
            "storage_ntfs_perf",
            "storage_disable_delivery_opt",
            "sys_disable_bing_widgets",
            "sys_raw_mouse_keyboard",
            "svc_disable_non_essential",
        ],
    ),
    Preset(
        id="extreme",
        name="Extreme / Potato PC Max FPS",
        badge="AGGRESSIVE",
        description="Gaming Pro + AFD socket buffers, Telemetry Hosts Blocker, Snappy UI (no animations), Disable Memory Compression & Hibernation.",
        tweak_ids=[
            "cpu_ultimate_power",
            "cpu_disable_core_parking",
            "cpu_disable_power_throttling",
            "cpu_win32_priority_gaming",
            "cpu_disable_hibernation",
            "cpu_usb_pcie_power",
            "gpu_hags_enable",
            "gpu_windowed_optimizations",
            "gpu_disable_gamedvr",
            "gpu_mmcss_gaming",
            "gpu_auto_game_boost",
            "net_disable_nagle",
            "net_tcp_gaming_stack",
            "net_afd_buffers",
            "net_nic_power_saving",
            "net_qos_reserve",
            "priv_telemetry_diag",
            "priv_disable_ai_copilot",
            "priv_debloat_edge",
            "priv_ads_spotlight",
            "priv_telemetry_tasks",
            "priv_hosts_blocker",
            "ram_svchost_auto",
            "ram_kernel_paging",
            "ram_disable_compression",
            "storage_ntfs_perf",
            "storage_disable_delivery_opt",
            "sys_disable_bing_widgets",
            "sys_snappy_ui",
            "sys_raw_mouse_keyboard",
            "svc_disable_non_essential",
        ],
    ),
]


def get_tweaks_by_category(category: str) -> list[Tweak]:
    return [t for t in ALL_TWEAKS if t.category == category]


def search_tweaks(query: str) -> list[Tweak]:
    q = query.strip().lower()
    if not q:
        return list(ALL_TWEAKS)
    return [
        t
        for t in ALL_TWEAKS
        if q in t.name.lower()
        or q in t.description.lower()
        or q in t.category.lower()
        or q in t.source.lower()
        or any(q in tag.lower() for tag in t.tags)
    ]


def get_preset_tweaks(preset_id: str) -> list[Tweak]:
    preset = next((p for p in PRESETS if p.id == preset_id), None)
    if not preset:
        return []
    return [TWEAK_BY_ID[tid] for tid in preset.tweak_ids if tid in TWEAK_BY_ID]


__all__ = [
    "ALL_TWEAKS",
    "CATEGORIES",
    "PRESETS",
    "TWEAK_BY_ID",
    "get_preset_tweaks",
    "get_tweaks_by_category",
    "search_tweaks",
]
