"""CLI & GUI entrypoint for Optimasi Windows."""

from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
from pathlib import Path

from optimasi import APP_NAME, APP_VERSION
from optimasi.core.admin import is_admin, is_compiled
from optimasi.core.cleaner import scan_junk
from optimasi.core.executor import TweakExecutor
from optimasi.core.health_score import evaluate_optimization_score
from optimasi.core.system_info import get_system_snapshot
from optimasi.core.updater import check_for_updates, is_newer_version
from optimasi.tweaks import ALL_TWEAKS, PRESETS, get_preset_tweaks

_MUTEX_HANDLE = None


def _acquire_single_instance_mutex() -> None:
    """Register named mutex for Inno Setup AppMutex & single-instance awareness."""
    global _MUTEX_HANDLE
    try:
        _MUTEX_HANDLE = ctypes.windll.kernel32.CreateMutexW(
            None, False, "OptimasiWindowsSingleInstanceMutex"
        )
    except Exception:
        pass


def run_self_test(out_path: str | None = None) -> dict:
    """Run offline, non-destructive verification checks (safe for Nuitka binary QA)."""
    import PySide6
    from PySide6 import QtWidgets  # noqa: F401

    snap = get_system_snapshot()
    score_data = evaluate_optimization_score()
    laptop_tweaks = get_preset_tweaks("laptop_pro")
    res = TweakExecutor(dry_run=True).run_tweaks(laptop_tweaks, session_label="SelfTest")
    junk_categories = scan_junk()

    report = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "python_version": platform.python_version(),
        "python_major_minor": list(sys.version_info[:2]),
        "compiled": is_compiled(),
        "is_admin": is_admin(),
        "pyside6_ok": True,
        "pyside6_version": getattr(PySide6, "__version__", "unknown"),
        "updater_semver_ok": is_newer_version("v9.9.9", APP_VERSION) and not is_newer_version(APP_VERSION, APP_VERSION),
        "tweak_count": len(ALL_TWEAKS),
        "preset_count": len(PRESETS),
        "health_score": score_data["score"],
        "dry_run_succeeded": res.succeeded,
        "dry_run_failed": res.failed,
        "dry_run_ok": res.failed == 0 and res.succeeded > 0,
        "junk_category_count": len(junk_categories),
        "device_model": f"{snap['manufacturer']} {snap['model']}",
        "is_laptop": snap["is_laptop"],
        "os_name": snap["os"]["name"],
        "gpu_primary_vendor": snap["gpu_primary_vendor"],
    }

    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="optimasi", description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument("--version", action="store_true", help="Print version and Python runtime info")
    parser.add_argument("--dry-run", action="store_true", help="Start GUI with Dry-Run mode enabled")
    parser.add_argument("--check-update", action="store_true", help="Check GitHub Releases for updates and exit")
    parser.add_argument("--self-test", action="store_true", help="Run non-destructive offline self-test and exit")
    parser.add_argument("--self-test-out", type=str, default=None, help="Write self-test JSON report to path")
    args = parser.parse_args(argv)

    if args.version:
        print(f"{APP_NAME} v{APP_VERSION} (Python {platform.python_version()}, compiled={is_compiled()})")
        return 0

    if args.check_update:
        info, err = check_for_updates()
        if err:
            print(f"Update check error: {err}")
            return 1
        if info:
            print(f"Update available: v{info.latest_version} -> {info.download_url}")
        else:
            print(f"Up to date (v{APP_VERSION}).")
        return 0

    if args.self_test or args.self_test_out:
        report = run_self_test(args.self_test_out)
        print(json.dumps(report, indent=2))
        return 0 if (report["dry_run_ok"] and report["pyside6_ok"]) else 1

    _acquire_single_instance_mutex()
    from optimasi.ui.main_window import run_gui

    return run_gui(start_dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
