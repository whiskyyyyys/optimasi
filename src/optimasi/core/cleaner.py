"""Disk junk scanner/cleaner, RAM working-set trimmer, and Windows system repair."""

from __future__ import annotations

import ctypes
import glob
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import psutil

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


@dataclass
class JunkCategoryStats:
    key: str
    label: str
    description: str
    paths: list[str]
    file_count: int = 0
    size_bytes: int = 0

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)


@dataclass
class CleanSummary:
    files_deleted: int = 0
    dirs_deleted: int = 0
    bytes_freed: int = 0
    skipped_locked: int = 0

    @property
    def mb_freed(self) -> float:
        return round(self.bytes_freed / (1024 * 1024), 2)


def get_default_junk_categories() -> list[dict]:
    """Return standard safe Windows junk/cache directory definitions."""
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    temp = os.environ.get("TEMP", "")
    windir = os.environ.get("WINDIR", r"C:\Windows")

    return [
        {
            "key": "user_temp",
            "label": "User Temporary Files",
            "description": "Temporary installer & app files in %TEMP%",
            "paths": [temp] if temp else [],
        },
        {
            "key": "windows_temp",
            "label": "Windows Temp & Prefetch",
            "description": "System temp & stale prefetch files",
            "paths": [str(Path(windir) / "Temp"), str(Path(windir) / "Prefetch")],
        },
        {
            "key": "shader_cache",
            "label": "GPU & DirectX Shader Caches",
            "description": "D3DSCache, NVIDIA DXCache/GLCache, AMD DxCache",
            "paths": [
                str(Path(local) / "D3DSCache"),
                str(Path(local) / "NVIDIA" / "DXCache"),
                str(Path(local) / "NVIDIA" / "GLCache"),
                str(Path(local) / "AMD" / "DxCache"),
            ] if local else [],
        },
        {
            "key": "explorer_cache",
            "label": "Explorer Thumbnail & Icon Cache",
            "description": "Windows Explorer thumbcache_*.db and iconcache_*.db",
            "paths": [
                str(Path(local) / "Microsoft" / "Windows" / "Explorer" / "thumbcache_*.db"),
                str(Path(local) / "Microsoft" / "Windows" / "Explorer" / "iconcache_*.db"),
                str(Path(local) / "IconCache.db"),
            ] if local else [],
        },
        {
            "key": "wu_cache",
            "label": "Windows Update Download Cache",
            "description": "Downloaded update installers in SoftwareDistribution\\Download",
            "paths": [str(Path(windir) / "SoftwareDistribution" / "Download")],
        },
        {
            "key": "crash_wer",
            "label": "Crash Dumps & Error Reports",
            "description": "Local CrashDumps and Windows Error Reporting (WER) archives",
            "paths": [
                str(Path(local) / "CrashDumps") if local else "",
                r"C:\ProgramData\Microsoft\Windows\WER\ReportArchive",
                r"C:\ProgramData\Microsoft\Windows\WER\ReportQueue",
            ],
        },
        {
            "key": "browser_cache",
            "label": "Browser Caches (Chrome/Edge/Brave/Opera/Firefox)",
            "description": "Cached web files only (preserves cookies, passwords & bookmarks)",
            "paths": [
                str(Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "Cache"),
                str(Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache"),
                str(Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache"),
                str(Path(local) / "Opera Software" / "Opera GX Stable" / "Cache"),
                str(Path(local) / "Mozilla" / "Firefox" / "Profiles" / "*" / "cache2"),
                str(Path(roaming) / "Microsoft" / "Windows" / "Recent"),
            ] if local and roaming else [],
        },
    ]


def _resolve_targets(patterns: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for pat in patterns:
        if not pat:
            continue
        if "*" in pat or "?" in pat:
            for match in glob.glob(pat):
                resolved.append(Path(match))
        else:
            p = Path(pat)
            if p.exists():
                resolved.append(p)
    return resolved


def scan_junk(categories_override: list[dict] | None = None) -> list[JunkCategoryStats]:
    """Scan junk categories and return file counts and sizes without modifying anything."""
    defs = categories_override if categories_override is not None else get_default_junk_categories()
    stats_list: list[JunkCategoryStats] = []

    for cat in defs:
        stats = JunkCategoryStats(
            key=cat["key"],
            label=cat["label"],
            description=cat["description"],
            paths=list(cat["paths"]),
        )
        for target in _resolve_targets(cat["paths"]):
            if target.is_file():
                try:
                    stats.file_count += 1
                    stats.size_bytes += target.stat().st_size
                except OSError:
                    pass
            elif target.is_dir():
                for root, _, files in os.walk(target, onerror=lambda _e: None):
                    for fname in files:
                        fpath = Path(root) / fname
                        try:
                            stats.file_count += 1
                            stats.size_bytes += fpath.stat().st_size
                        except OSError:
                            pass
        stats_list.append(stats)

    return stats_list


def clean_junk(
    selected_keys: list[str],
    categories_override: list[dict] | None = None,
    include_recycle_bin: bool = False,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> CleanSummary:
    """Safely delete contents of selected junk categories, skipping locked files."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    defs = categories_override if categories_override is not None else get_default_junk_categories()
    summary = CleanSummary()
    selected_set = set(selected_keys)

    for cat in defs:
        if cat["key"] not in selected_set:
            continue
        targets = _resolve_targets(cat["paths"])
        log(f"Cleaning {cat['label']}...")
        for target in targets:
            if target.is_file():
                _remove_file(target, summary, dry_run)
            elif target.is_dir():
                for child in list(target.iterdir()):
                    if child.is_file() or child.is_symlink():
                        _remove_file(child, summary, dry_run)
                    elif child.is_dir():
                        _remove_tree_best_effort(child, summary, dry_run)

    if include_recycle_bin:
        if dry_run:
            log("[DRY-RUN] Would empty Windows Recycle Bin.")
        else:
            log("Emptying Windows Recycle Bin...")
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True,
                creationflags=_CREATE_NO_WINDOW,
            )

    prefix = "[DRY-RUN] " if dry_run else ""
    log(
        f"{prefix}Cleanup finished: {summary.files_deleted} files (~{summary.mb_freed} MB), "
        f"{summary.skipped_locked} locked files skipped."
    )
    return summary


def _remove_file(path: Path, summary: CleanSummary, dry_run: bool) -> None:
    try:
        size = path.stat().st_size
        if not dry_run:
            path.unlink()
        summary.files_deleted += 1
        summary.bytes_freed += size
    except OSError:
        summary.skipped_locked += 1


def _remove_tree_best_effort(folder: Path, summary: CleanSummary, dry_run: bool) -> None:
    for root, dirs, files in os.walk(folder, topdown=False, onerror=lambda _e: None):
        for fname in files:
            _remove_file(Path(root) / fname, summary, dry_run)
        for dname in dirs:
            dpath = Path(root) / dname
            try:
                if not dry_run:
                    dpath.rmdir()
                summary.dirs_deleted += 1
            except OSError:
                pass
    try:
        if not dry_run:
            folder.rmdir()
        summary.dirs_deleted += 1
    except OSError:
        pass


def trim_ram_working_sets(
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[int, int]:
    """Trim working-set memory of accessible user/system processes via Win32 EmptyWorkingSet."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    if dry_run:
        count = sum(1 for _ in psutil.process_iter())
        log(f"[DRY-RUN] Would trim working-set memory across ~{count} processes.")
        return count, 0

    before_avail = psutil.virtual_memory().available / (1024 * 1024)
    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_SET_QUOTA = 0x0100

    trimmed = 0
    skipped = 0
    for proc in psutil.process_iter(["pid", "name"]):
        pid = proc.info["pid"]
        if pid <= 4:
            continue
        handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
        if not handle:
            skipped += 1
            continue
        try:
            if psapi.EmptyWorkingSet(handle):
                trimmed += 1
            else:
                skipped += 1
        finally:
            kernel32.CloseHandle(handle)

    after_avail = psutil.virtual_memory().available / (1024 * 1024)
    delta = round(max(0.0, after_avail - before_avail), 1)
    log(f"Trimmed {trimmed} processes ({skipped} protected skipped). Available RAM gained: ~{delta} MB")
    return trimmed, skipped


def run_system_repair(
    mode: str,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Run Windows built-in repair / SSD TRIM / network reset utilities."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    commands: dict[str, tuple[str, list[str]]] = {
        "dism_restore": ("DISM Image RestoreHealth", ["DISM.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"]),
        "dism_cleanup": ("DISM WinSxS Component Cleanup", ["DISM.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"]),
        "sfc": ("System File Checker (sfc /scannow)", ["sfc", "/scannow"]),
        "ssd_trim": ("SSD ReTrim (Optimize-Volume C:)", ["powershell", "-NoProfile", "-Command", "Optimize-Volume -DriveLetter C -ReTrim -Verbose"]),
        "flush_dns": ("Flush DNS Resolver Cache", ["ipconfig", "/flushdns"]),
        "network_reset": ("Reset Winsock & TCP/IP Stack", ["cmd", "/c", "netsh winsock reset && netsh int ip reset && ipconfig /flushdns"]),
    }

    if mode not in commands:
        return False, f"Unknown repair mode: {mode}"

    label, cmd = commands[mode]
    if dry_run:
        msg = f"[DRY-RUN] Would run {label}: {' '.join(cmd)}"
        log(msg)
        return True, msg

    log(f"Running {label}... (this may take a few minutes for DISM/SFC)")
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            creationflags=_CREATE_NO_WINDOW,
        )
        output = (res.stdout or res.stderr or "").strip()
        for line in output.splitlines()[-12:]:
            if line.strip():
                log(f"  {line.strip()}")
        if res.returncode == 0:
            msg = f"{label} completed successfully."
            log(msg)
            return True, msg
        msg = f"{label} exited with code {res.returncode}."
        log(msg)
        return False, msg
    except Exception as exc:
        msg = f"{label} error: {exc}"
        log(msg)
        return False, msg
