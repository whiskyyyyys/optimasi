"""Nuitka + Inno Setup 6 build script for Optimasi Windows (requires Python 3.11)."""

from __future__ import annotations

import argparse
import os
import shutil
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
    env = os.environ.copy()
    parts = env.get("PATH", "").split(os.pathsep)
    filtered = [p for p in parts if "mingw" not in p.lower() and "winlibs" not in p.lower()]
    env["PATH"] = os.pathsep.join(filtered)
    return env


def _find_iscc() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    on_path = shutil.which("ISCC")
    return Path(on_path) if on_path else None


def build_nuitka(uac_admin: bool = True, force_managed_gcc: bool = False) -> int:
    ensure_python_311()
    icon_path = ROOT / "assets" / "app.ico"
    ensure_icon(icon_path)

    dist_dir = ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Clean previous standalone folder so Inno Setup only packages fresh files
    target_dir = dist_dir / "OptimasiWindows"
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    entry = ROOT / "src" / "optimasi" / "main.py"
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--mingw64",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--include-qt-plugins=sensible,styles,iconengines,imageformats,platforms",
        "--include-package=optimasi",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        "--windows-console-mode=disable",
        f"--windows-icon-from-ico={icon_path}",
        "--company-name=WhisXD",
        "--product-name=Optimasi Windows",
        "--file-version=2.1.2.0",
        "--product-version=2.1.2.0",
        "--file-description=Modern Windows Performance, Laptop & Gaming Optimizer",
        f"--output-dir={dist_dir}",
        "--output-filename=OptimasiWindows.exe",
        str(entry),
    ]
    if uac_admin:
        cmd.append("--windows-uac-admin")
    cmd.append("--remove-output")

    env = _sanitized_env_without_external_gcc() if force_managed_gcc else os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    print("Running Nuitka standalone build:")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
    if proc.returncode != 0 and not force_managed_gcc:
        print("\n[INFO] Retrying Nuitka with Nuitka-managed WinLibs MinGW64 toolchain...")
        env = _sanitized_env_without_external_gcc()
        env["PYTHONPATH"] = str(ROOT / "src")
        proc = subprocess.run(cmd, cwd=str(ROOT), env=env)

    if proc.returncode != 0:
        return proc.returncode

    # Normalize Nuitka main.dist -> dist/OptimasiWindows
    main_dist = dist_dir / "main.dist"
    if main_dist.exists():
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        main_dist.rename(target_dir)

    return 0


def build_installer() -> int:
    iscc = _find_iscc()
    iss_file = ROOT / "installer" / "OptimasiWindows.iss"
    if not iscc:
        print("WARNING: Inno Setup 6 (ISCC.exe) not found; skipping .exe installer creation.")
        return 0
    if not iss_file.exists():
        print(f"ERROR: Missing installer script {iss_file}")
        return 1
    print(f"\nBuilding Windows Installer with {iscc}...")
    proc = subprocess.run([str(iscc), str(iss_file)], cwd=str(ROOT))
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Optimasi Windows with Nuitka + Inno Setup 6")
    parser.add_argument("--no-uac-admin", action="store_true", help="Do not embed Windows UAC admin manifest in exe")
    parser.add_argument("--managed-gcc", action="store_true", help="Force Nuitka-managed WinLibs GCC")
    parser.add_argument("--skip-installer", action="store_true", help="Skip Inno Setup packaging")
    args = parser.parse_args()

    rc = build_nuitka(uac_admin=not args.no_uac_admin, force_managed_gcc=args.managed_gcc)
    if rc != 0:
        return rc
    if not args.skip_installer:
        return build_installer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
