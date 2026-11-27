"""Administrator privilege detection and UAC elevation helpers."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path


def is_compiled() -> bool:
    """Return True if running inside a compiled Nuitka or frozen executable."""
    return bool(
        "__compiled__" in globals()
        or getattr(sys, "frozen", False)
        or hasattr(sys, "__compiled__")
    )


def is_admin() -> bool:
    """Return True if the current process holds Windows Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin(extra_args: list[str] | None = None) -> bool:
    """Relaunch the current application with a UAC elevation prompt.

    Returns True if ShellExecuteW succeeded (> 32), False otherwise.
    """
    args = list(extra_args) if extra_args is not None else sys.argv[1:]
    if is_compiled():
        executable = sys.executable
        params = " ".join(f'"{arg}"' if " " in arg else arg for arg in args)
    else:
        executable = sys.executable
        script_or_mod = ["-m", "optimasi.main"]
        main_mod = sys.modules.get("__main__")
        main_file = getattr(main_mod, "__file__", None)
        if main_file and Path(main_file).exists() and Path(main_file).name != "pytest":
            script_or_mod = [f'"{main_file}"']
        all_args = script_or_mod + [f'"{arg}"' if " " in arg else arg for arg in args]
        params = " ".join(all_args)

    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
        return int(rc) > 32
    except Exception:
        return False
