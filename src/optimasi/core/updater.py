"""In-app GitHub Releases auto-updater and user settings persistence."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from optimasi import APP_NAME, APP_VERSION, REPO_SLUG

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
_DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)


@dataclass(slots=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    tag_name: str
    release_name: str
    changelog: str
    download_url: str
    asset_name: str
    asset_size: int
    html_url: str
    is_installer: bool


def get_app_data_dir() -> Path:
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    d = local / "OptimasiWindows"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_settings_path() -> Path:
    return get_app_data_dir() / "settings.json"


def load_settings() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "auto_check_updates": True,
        "minimize_to_tray": True,
        "last_skipped_version": "",
    }
    p = get_settings_path()
    if not p.exists():
        return defaults
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            defaults.update(data)
    except Exception:
        pass
    return defaults


def save_settings(settings: dict[str, Any]) -> None:
    p = get_settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def parse_semver(tag: str) -> tuple[int, int, int]:
    """Parse tag/version like 'v2.1.0' or '2.0.1-beta' into (major, minor, patch)."""
    cleaned = tag.strip().lstrip("vV")
    nums = re.findall(r"\d+", cleaned)
    parts = [int(x) for x in nums[:3]]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]


def is_newer_version(latest_tag: str, current_version: str = APP_VERSION) -> bool:
    """Return True if latest_tag is strictly newer than current_version."""
    return parse_semver(latest_tag) > parse_semver(current_version)


def select_release_asset(assets: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer Inno Setup installer (*Setup*.exe), else portable OptimasiWindows*.exe."""
    exe_assets = [
        a for a in assets
        if str(a.get("name", "")).lower().endswith(".exe") and a.get("browser_download_url")
    ]
    if not exe_assets:
        return None
    for a in exe_assets:
        name = str(a.get("name", "")).lower()
        if "setup" in name or "installer" in name:
            return a
    for a in exe_assets:
        if "optimasiwindows" in str(a.get("name", "")).lower():
            return a
    return exe_assets[0]


def check_for_updates(
    current_version: str = APP_VERSION,
    repo: str = REPO_SLUG,
    timeout: int = 8,
) -> tuple[UpdateInfo | None, str | None]:
    """Query GitHub Releases API for a newer version.

    Returns (UpdateInfo | None, error_message | None).
    """
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_NAME}/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, None
        return None, f"GitHub API HTTP {exc.code}"
    except Exception as exc:
        return None, f"Update check failed: {exc}"

    tag = str(data.get("tag_name") or "").strip()
    if not tag or not is_newer_version(tag, current_version):
        return None, None

    asset = select_release_asset(data.get("assets") or [])
    if not asset:
        return None, "New release found, but no Windows .exe asset is attached yet."

    asset_name = str(asset.get("name", "OptimasiWindows-Setup.exe"))
    is_installer = "setup" in asset_name.lower() or "installer" in asset_name.lower()
    return (
        UpdateInfo(
            current_version=current_version,
            latest_version=tag.lstrip("vV"),
            tag_name=tag,
            release_name=str(data.get("name") or tag),
            changelog=str(data.get("body") or "No release notes provided."),
            download_url=str(asset["browser_download_url"]),
            asset_name=asset_name,
            asset_size=int(asset.get("size") or 0),
            html_url=str(data.get("html_url") or f"https://github.com/{repo}/releases"),
            is_installer=is_installer,
        ),
        None,
    )


def download_update(
    update: UpdateInfo,
    progress_cb: Callable[[int, int, float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    timeout: int = 30,
) -> Path:
    """Download the release asset to a temporary folder with progress reporting."""
    dl_dir = Path(tempfile.gettempdir()) / "OptimasiWindowsUpdate"
    dl_dir.mkdir(parents=True, exist_ok=True)
    target = dl_dir / update.asset_name

    req = urllib.request.Request(
        update.download_url,
        headers={"User-Agent": f"{APP_NAME}/{update.current_version}"},
    )
    start_t = time.monotonic()
    downloaded = 0

    with urllib.request.urlopen(req, timeout=timeout) as resp, target.open("wb") as fp:
        total = int(resp.headers.get("Content-Length") or update.asset_size or 0)
        while True:
            if cancel_check and cancel_check():
                raise RuntimeError("Update download cancelled.")
            chunk = resp.read(65536)
            if not chunk:
                break
            fp.write(chunk)
            downloaded += len(chunk)
            elapsed = max(0.05, time.monotonic() - start_t)
            speed_kbps = (downloaded / 1024.0) / elapsed
            if progress_cb:
                progress_cb(downloaded, total, speed_kbps)

    return target


def launch_update_installer(
    downloaded_path: Path,
    is_installer: bool,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Launch the downloaded installer silently (or swap portable exe) and return status."""
    if not dry_run and not downloaded_path.exists():
        return False, f"Downloaded update not found: {downloaded_path}"

    if is_installer:
        cmd = [
            str(downloaded_path),
            "/SILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/RESTARTAPPLICATIONS",
        ]
        if dry_run:
            return True, f"[DRY-RUN] Would launch silent installer: {' '.join(cmd)}"
        subprocess.Popen(
            cmd,
            creationflags=_DETACHED_PROCESS | _CREATE_NO_WINDOW,
            close_fds=True,
        )
        return True, "Installer launched for silent upgrade and automatic restart."

    # Fallback for portable exe replacement
    current_exe = Path(sys.executable)
    cmd_script = downloaded_path.parent / "apply_update.cmd"
    if dry_run:
        return True, f"[DRY-RUN] Would replace {current_exe} with {downloaded_path}"

    pid = os.getpid()
    script_text = (
        "@echo off\n"
        f":wait_loop\n"
        f"tasklist /FI \"PID eq {pid}\" 2>NUL | find /I \"{pid}\" >NUL\n"
        "if not errorlevel 1 (\n"
        "  timeout /t 1 /nobreak >NUL\n"
        "  goto wait_loop\n"
        ")\n"
        f"copy /Y \"{downloaded_path}\" \"{current_exe}\" >NUL\n"
        f"start \"\" \"{current_exe}\"\n"
    )
    cmd_script.write_text(script_text, encoding="utf-8")
    subprocess.Popen(
        ["cmd.exe", "/c", str(cmd_script)],
        creationflags=_DETACHED_PROCESS | _CREATE_NO_WINDOW,
        close_fds=True,
    )
    return True, "Portable update swapper launched."
