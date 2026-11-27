"""Nuitka build script for Optimasi Windows (requires Python 3.11)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def ensure_python_311() -> None:
    if sys.version_info[:2] != (3, 11):
        raise SystemExit(
            f"ERROR: Nuitka build requires Python 3.11, but got {sys.version_info.major}.{sys.version_info.minor}."
        )


def ensure_icon(icon_path: Path) -> None:
    if icon_path.exists():
        return
    from PIL import Image, ImageDraw

    icon_path.parent.mkdir(parents=True, exist_ok=True)
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([12, 12, 244, 244], radius=48, fill=(13, 19, 33, 255), outline=(6, 182, 212, 255), width=10)
    d.polygon(
        [(128, 36), (206, 68), (196, 154), (128, 218), (60, 154), (50, 68)],
        fill=(17, 28, 48, 255),
        outline=(34, 211, 238, 255),
        width=6,
    )
    d.polygon([(138, 66), (88, 138), (126, 138), (114, 194), (168, 118), (130, 118)], fill=(34, 211, 238, 255))
    img.save(icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def _sanitized_env_without_external_gcc() -> dict[str, str]:
    """Strip pre-installed MinGW/WinLibs GCC from PATH so Nuitka uses its managed WinLibs toolchain."""
    env = os.environ.copy()
    parts = env.get("PATH", "").split(os.pathsep)
    filtered = [
        p
        for p in parts
        if "mingw" not in p.lower() and "winlibs" not in p.lower()
    ]
    env["PATH"] = os.pathsep.join(filtered)
    return env


def build(standalone: bool = False, uac_admin: bool = False, force_managed_gcc: bool = False) -> int:
    ensure_python_311()
    icon_path = ROOT / "assets" / "app.ico"
    ensure_icon(icon_path)

    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    entry = ROOT / "src" / "optimasi" / "main.py"

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone" if standalone else "--onefile",
        "--mingw64",
        "--assume-yes-for-downloads",
        "--enable-plugin=tk-inter",
        "--include-package=optimasi",
        "--include-package-data=customtkinter",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={icon_path}",
        "--company-name=WhisXD",
        "--product-name=Optimasi Windows",
        "--file-version=1.0.0.0",
        "--product-version=1.0.0.0",
        "--file-description=Windows Performance, Gaming, Privacy & Debloat Optimizer",
        f"--output-dir={dist_dir}",
        "--output-filename=OptimasiWindows.exe",
        "--remove-output",
    ]
    if uac_admin:
        cmd.append("--windows-uac-admin")
    cmd.append(str(entry))

    env = _sanitized_env_without_external_gcc() if force_managed_gcc else os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    print("Running Nuitka build:")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    if proc.returncode != 0 and not force_managed_gcc:
        print("\n[INFO] Retrying Nuitka with Nuitka-managed WinLibs MinGW64 toolchain...")
        env = _sanitized_env_without_external_gcc()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Optimasi Windows with Nuitka + Python 3.11")
    parser.add_argument("--standalone", action="store_true", help="Build standalone folder instead of single-file .exe")
    parser.add_argument("--uac-admin", action="store_true", help="Embed Windows UAC admin manifest in exe")
    parser.add_argument("--managed-gcc", action="store_true", help="Force Nuitka-managed WinLibs GCC")
    args = parser.parse_args()
    return build(standalone=args.standalone, uac_admin=args.uac_admin, force_managed_gcc=args.managed_gcc)


if __name__ == "__main__":
    raise SystemExit(main())
