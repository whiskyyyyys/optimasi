"""Dedicated Game Profiles, Roblox FFlags Optimizer, and ADVAN 1701 (Ryzen 5 6600H + Radeon 660M) recommendations."""

from __future__ import annotations

import json
import os
import winreg
from pathlib import Path
from typing import Any, Callable

ROBLOX_FFLAGS_PROFILES: dict[str, dict[str, Any]] = {
    "smooth_660m": {
        "label": "Roblox Smooth 120 FPS (Recommended ADVAN 1701)",
        "fflags": {
            "DFIntTaskSchedulerTargetFps": 120,
            "FFlagDebugGraphicsPreferD3D11": True,
            "FFlagDisablePostFx": True,
            "FIntRenderShadowIntensity": 0,
            "DFFlagTextureQualityOverrideEnabled": True,
            "DFIntTextureQualityOverride": 2,
            "FFlagDebugDisableTelemetryEphemeralCounter": True,
            "FFlagDebugDisableTelemetryEphemeralStat": True,
            "FFlagDebugDisableTelemetryEventIngest": True,
            "FFlagDebugDisableTelemetryPoint": True,
            "FFlagDebugDisableTelemetryV2Counter": True,
            "FFlagDebugDisableTelemetryV2Event": True,
            "FFlagDebugDisableTelemetryV2Stat": True,
        },
    },
    "ultra_fps": {
        "label": "Roblox Ultra FPS / Heavy Maps (240 Cap)",
        "fflags": {
            "DFIntTaskSchedulerTargetFps": 240,
            "FFlagDebugGraphicsPreferD3D11": True,
            "FFlagDisablePostFx": True,
            "FIntRenderShadowIntensity": 0,
            "DFFlagTextureQualityOverrideEnabled": True,
            "DFIntTextureQualityOverride": 0,
            "FFlagRenderNoLowFrmBloom": True,
            "FFlagDebugDisableTelemetryEphemeralCounter": True,
            "FFlagDebugDisableTelemetryEphemeralStat": True,
            "FFlagDebugDisableTelemetryEventIngest": True,
            "FFlagDebugDisableTelemetryPoint": True,
            "FFlagDebugDisableTelemetryV2Counter": True,
            "FFlagDebugDisableTelemetryV2Event": True,
            "FFlagDebugDisableTelemetryV2Stat": True,
        },
    },
}

RECOMMENDED_GAMES_660M: list[dict[str, str]] = [
    {
        "name": "Roblox (Blox Fruits / Anime Defenders / Brookhaven)",
        "genre": "Sandbox / Online Multiplayer",
        "expected_fps": "120+ FPS",
        "best_settings": "D3D11 + No PostFx + Shadow Off (pakai profil Roblox Smooth 120 FPS di atas), Graphics 5–7",
        "profile_id": "roblox",
        "note": "Sangat ringan dan mulus di Radeon 660M dengan FFlags Smooth 120 FPS.",
    },
    {
        "name": "Valorant",
        "genre": "Competitive Tactical FPS",
        "expected_fps": "130–180 FPS",
        "best_settings": "1920x1200 / 1080p Low, Multithreaded Rendering ON, VSync OFF, Raw Mouse 1:1",
        "profile_id": "valorant",
        "note": "Ryzen 5 6600H (6C/12T) sangat kuat untuk game CPU-bound seperti Valorant.",
    },
    {
        "name": "Minecraft (Java + Sodium / Bedrock)",
        "genre": "Sandbox / Survival",
        "expected_fps": "180–300+ FPS",
        "best_settings": "Render Distance 12–16 Chunks, Sodium/Iris Mod, Allocate 4 GB RAM",
        "profile_id": "minecraft",
        "note": "Pakai modpack Fabulously Optimized / Sodium di Java Edition untuk FPS maksimal.",
    },
    {
        "name": "MuMuPlayer (Mobile Legends / PUBG / Free Fire)",
        "genre": "Android Emulator Gaming",
        "expected_fps": "60–120 FPS",
        "best_settings": "Graphics DirectX/Vulkan, 4 CPU Cores, 4 GB RAM, High Performance GPU",
        "profile_id": "mumuplayer",
        "note": "Sudah terdeteksi di C:\\Program Files\\Netease\\MuMuPlayer — wajib set High Perf GPU.",
    },
    {
        "name": "GTA V / FiveM Roleplay",
        "genre": "Open World Action",
        "expected_fps": "60–75 FPS",
        "best_settings": "1080p Normal–High, Grass Quality Normal, MSAA Off, Texture High",
        "profile_id": "gtav",
        "note": "Jangan set Grass ke High/Ultra karena memakan iGPU; Normal sudah sangat stabil 60+ FPS.",
    },
    {
        "name": "Genshin Impact / Honkai: Star Rail",
        "genre": "Action RPG / Gacha",
        "expected_fps": "55–60 FPS",
        "best_settings": "1080p Medium, Render Resolution 1.0, Shadows Low, Motion Blur Off",
        "profile_id": "genshin",
        "note": "Stabil di 60 FPS pada resolusi 1080p Medium dengan suhu laptop tetap terjaga.",
    },
    {
        "name": "Counter-Strike 2 (CS2)",
        "genre": "Competitive FPS",
        "expected_fps": "75–105 FPS",
        "best_settings": "1600x900 atau 1920x1080 Low, FidelityFX Super Resolution (FSR) Quality",
        "profile_id": "cs2",
        "note": "Aktifkan FSR Quality agar tajam sekaligus tembus 80+ FPS di match 5v5.",
    },
    {
        "name": "Hades / Hollow Knight / Left 4 Dead 2 / Stardew Valley",
        "genre": "Indie / Co-op Classics",
        "expected_fps": "120–240 FPS",
        "best_settings": "1920x1200 High/Ultra, VSync Off",
        "profile_id": "indie",
        "note": "Super adem, baterai awet, dan nyaman dimainkan di layar 1200p ADVAN 1701.",
    },
]


def find_roblox_version_dirs() -> list[Path]:
    """Find installed Roblox, Bloxstrap, and Fishstrap folders that accept ClientSettings."""
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    dirs: list[Path] = []

    for base in [
        local / "Roblox" / "Versions",
        Path(r"C:\Program Files (x86)\Roblox\Versions"),
    ]:
        if base.exists():
            for ver in sorted(base.glob("version-*"), reverse=True):
                if (ver / "RobloxPlayerBeta.exe").exists():
                    dirs.append(ver)

    for strap in [local / "Bloxstrap" / "Modifications", local / "Fishstrap" / "Modifications"]:
        if strap.exists():
            dirs.append(strap)

    # Also support global Roblox ClientSettings fallback if Roblox folder exists
    roblox_root = local / "Roblox"
    if roblox_root.exists() and not dirs:
        dirs.append(roblox_root)

    return dirs


def apply_roblox_fflags(
    profile_key: str = "smooth_660m",
    target_dirs: list[Path] | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Write ClientSettings/ClientAppSettings.json for Roblox FPS & latency optimization."""
    if profile_key not in ROBLOX_FFLAGS_PROFILES:
        return False, f"Profil Roblox tidak dikenal: {profile_key}"

    profile = ROBLOX_FFLAGS_PROFILES[profile_key]
    dirs = target_dirs if target_dirs is not None else find_roblox_version_dirs()
    if not dirs:
        return False, "Folder instalasi Roblox tidak ditemukan. Buka Roblox minimal sekali lalu coba lagi."

    if dry_run:
        return True, f"[DRY-RUN] Would write {profile['label']} FFlags to {len(dirs)} Roblox folder(s)."

    written = 0
    for root in dirs:
        cs_dir = root / "ClientSettings"
        cs_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cs_dir / "ClientAppSettings.json"

        existing: dict[str, Any] = {}
        if cfg_file.exists():
            try:
                existing = json.loads(cfg_file.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}

        existing.update(profile["fflags"])
        cfg_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        written += 1

    return True, f"Berhasil menerapkan '{profile['label']}' ke {written} lokasi Roblox."


def revert_roblox_fflags(
    target_dirs: list[Path] | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Remove ClientAppSettings.json to restore default Roblox graphics & FPS settings."""
    dirs = target_dirs if target_dirs is not None else find_roblox_version_dirs()
    if not dirs:
        return True, "Tidak ada folder Roblox yang perlu dikembalikan."

    if dry_run:
        return True, f"[DRY-RUN] Would remove custom Roblox FFlags from {len(dirs)} folder(s)."

    removed = 0
    for root in dirs:
        cfg_file = root / "ClientSettings" / "ClientAppSettings.json"
        if cfg_file.exists():
            try:
                cfg_file.unlink()
                removed += 1
            except OSError:
                pass
    return True, f"Pengaturan Roblox dikembalikan ke default ({removed} file FFlags dihapus)."


def clean_roblox_cache(
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[int, float]:
    """Clean Roblox logs, temp downloads, and stale crash files without touching login cookies."""
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    temp = Path(os.environ.get("TEMP", local / "Temp"))
    targets = [
        local / "Roblox" / "logs",
        local / "Roblox" / "Downloads",
        temp / "Roblox",
    ]

    deleted = 0
    freed_bytes = 0
    for folder in targets:
        if not folder.exists():
            continue
        for root, _, files in os.walk(folder, onerror=lambda _e: None):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    sz = fpath.stat().st_size
                    if not dry_run:
                        fpath.unlink()
                    deleted += 1
                    freed_bytes += sz
                except OSError:
                    continue

    mb = round(freed_bytes / (1024 * 1024), 2)
    msg = (
        f"[DRY-RUN] Would clean {deleted} Roblox cache/log files (~{mb} MB)."
        if dry_run
        else f"Cache Roblox dibersihkan: {deleted} file (~{mb} MB lega)."
    )
    if log_cb:
        log_cb(msg)
    return deleted, mb


def discover_game_profile_exes(profile_id: str) -> list[str]:
    """Locate executables for a specific game or emulator profile."""
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    found: list[str] = []

    if profile_id == "roblox":
        for d in find_roblox_version_dirs():
            for exe_name in ("RobloxPlayerBeta.exe", "RobloxStudioBeta.exe"):
                p = d / exe_name
                if p.exists():
                    found.append(str(p))
    elif profile_id == "mumuplayer":
        for base in [
            Path(r"C:\Program Files\Netease\MuMuPlayer"),
            Path(r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0"),
            Path(r"C:\Program Files\Netease\MuMu Player 12"),
            Path(r"C:\Program Files\BlueStacks_nxt"),
            Path(r"C:\LDPlayer\LDPlayer9"),
        ]:
            if base.exists():
                for exe_name in ("MuMuPlayer.exe", "MuMuNxMain.exe", "MuMuNxDevice.exe", "MuMuVMMHeadless.exe", "HD-Player.exe", "dnplayer.exe"):
                    for match in base.rglob(exe_name):
                        found.append(str(match))
    elif profile_id == "valorant":
        for p in [
            Path(r"C:\Riot Games\VALORANT\live\VALORANT.exe"),
            Path(r"C:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe"),
            Path(r"C:\Program Files\Epic Games\VALORANT\VALORANT.exe"),
        ]:
            if p.exists():
                found.append(str(p))
    elif profile_id == "minecraft":
        for base in [
            roaming / ".minecraft" / "runtime",
            Path(r"C:\Program Files\Java"),
            Path(r"C:\Program Files\Eclipse Adoptium"),
            Path(r"C:\XboxGames\Minecraft Launcher\Content"),
        ]:
            if base.exists():
                for match in base.rglob("javaw.exe"):
                    found.append(str(match))
    elif profile_id == "gtav":
        for p in [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\Grand Theft Auto V\GTA5.exe"),
            Path(r"C:\Program Files\Epic Games\GTAV\GTAV.exe"),
            Path(r"C:\Program Files\Rockstar Games\Grand Theft Auto V\GTA5.exe"),
            local / "FiveM" / "FiveM.exe",
        ]:
            if p.exists():
                found.append(str(p))
    elif profile_id == "genshin":
        for p in [
            Path(r"C:\Program Files\Genshin Impact\Genshin Impact Game\GenshinImpact.exe"),
            Path(r"C:\Program Files\Epic Games\Genshin Impact\Genshin Impact Game\GenshinImpact.exe"),
            Path(r"C:\Program Files\Star Rail\Games\StarRail.exe"),
        ]:
            if p.exists():
                found.append(str(p))
    elif profile_id == "cs2":
        p = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\cs2.exe")
        if p.exists():
            found.append(str(p))

    return list(dict.fromkeys(found))


def apply_game_windows_boost(profile_id: str, dry_run: bool = False) -> tuple[bool, str]:
    """Apply High-Performance GPU, High CPU Priority, and Fullscreen Opt flags to a game profile."""
    exes = discover_game_profile_exes(profile_id)
    if not exes:
        return True, f"Executable untuk '{profile_id}' belum ditemukan di path standar (optimasi sistem global tetap aman)."

    if dry_run:
        return True, f"[DRY-RUN] Would boost {len(exes)} executable(s) for '{profile_id}'."

    gpu_pref_key = r"Software\Microsoft\DirectX\UserGpuPreferences"
    layers_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
    for exe_path in exes:
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

    return True, f"Optimasi Windows diterapkan ke {len(exes)} executable '{profile_id}' (High Perf GPU + High CPU Priority)."
