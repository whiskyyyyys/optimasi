"""Aggregated Windows optimization tweaks catalog and tailored presets."""

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
        id="laptop_pro",
        name="Laptop Ryzen/iGPU Pro",
        badge="BEST FOR YOUR LAPTOP",
        description=(
            "Dirancang khusus untuk laptop modern (Ryzen 6000H / Intel + iGPU 16 GB RAM): "
            "performa penuh saat colok charger, hemat baterai saat DC, optimasi AMD Radeon & Emulator (MuMuPlayer), "
            "tetap menjaga Memory Compression, Wi-Fi, Bluetooth & Sleep aman."
        ),
        tweak_ids=[
            "cpu_laptop_ac_dc_smart",
            "cpu_disable_power_throttling",
            "cpu_win32_priority_gaming",
            "cpu_amd_ryzen",
            "gpu_hags_enable",
            "gpu_windowed_optimizations",
            "gpu_disable_gamedvr",
            "gpu_mmcss_gaming",
            "gpu_amd_radeon",
            "gpu_auto_game_boost",
            "net_disable_nagle",
            "net_tcp_gaming_stack",
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
        id="laptop_battery",
        name="Laptop Cool & Battery Saver",
        badge="COOL & QUIET",
        description=(
            "Menjaga suhu laptop tetap adem & kipas senyap (cap CPU 99% AC / 80% DC), "
            "mematikan telemetry & background bloat Edge/Copilot agar baterai lebih awet."
        ),
        tweak_ids=[
            "cpu_laptop_cool_silent",
            "priv_telemetry_diag",
            "priv_disable_ai_copilot",
            "priv_debloat_edge",
            "priv_ads_spotlight",
            "priv_telemetry_tasks",
            "ram_svchost_auto",
            "storage_ntfs_perf",
            "storage_disable_delivery_opt",
            "sys_disable_bing_widgets",
            "svc_disable_non_essential",
        ],
    ),
    Preset(
        id="gaming_pro",
        name="Gaming & Emulator Max FPS",
        badge="FPS + LOW PING",
        description=(
            "Ultimate Performance, unparked CPU cores, HAGS, MMCSS Gaming, Nagle/TCP fix, "
            "Raw Mouse 1:1, dan Auto-Game/Emulator Boost untuk FPS maksimal saat plugged-in."
        ),
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
        id="safe_daily",
        name="Safe Daily Driver",
        badge="ZERO RISK",
        description=(
            "Optimasi harian paling aman: matikan telemetry, AI Copilot, Edge bloat, Bing Search, "
            "perbaiki NTFS/RAM, dan rapikan context menu Windows 11."
        ),
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
