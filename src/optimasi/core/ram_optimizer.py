"""Deep Windows RAM Optimizer: Working-Set Trimmer, Standby List Purge & System File Cache Flush."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Any, Callable

import psutil

from optimasi.core.admin import is_admin
from optimasi.core.cleaner import trim_ram_working_sets

_SYSTEM_MEMORY_LIST_INFORMATION = 80
_MEMORY_PURGE_STANDBY_LIST = 4
_MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST = 5


class _PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", wintypes.DWORD),
        ("ProcessCount", wintypes.DWORD),
        ("ThreadCount", wintypes.DWORD),
    ]


class _LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class _LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", _LUID), ("Attributes", wintypes.DWORD)]


class _TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", _LUID_AND_ATTRIBUTES * 1)]


def _enable_privilege(priv_name: str) -> bool:
    """Attempt to enable a Windows token privilege (e.g. SeProfileSingleProcessPrivilege)."""
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY = 0x0008
        SE_PRIVILEGE_ENABLED = 0x00000002

        h_token = wintypes.HANDLE()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h_token)):
            return False
        try:
            luid = _LUID()
            if not advapi32.LookupPrivilegeValueW(None, priv_name, ctypes.byref(luid)):
                return False
            tp = _TOKEN_PRIVILEGES()
            tp.PrivilegeCount = 1
            tp.Privileges[0].Luid = luid
            tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
            ok = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), ctypes.sizeof(tp), None, None)
            last_err = kernel32.GetLastError()
            return bool(ok) and last_err == 0
        finally:
            kernel32.CloseHandle(h_token)
    except Exception:
        return False


def get_memory_details() -> dict[str, Any]:
    """Return accurate physical, active, cached/standby, free, and commit memory stats."""
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    total_gb = round(vm.total / (1024**3), 2)
    available_gb = round(vm.available / (1024**3), 2)
    used_gb = round(vm.used / (1024**3), 2)
    cached_gb = 0.0
    free_gb = available_gb
    commit_used_gb = round(swap.used / (1024**3), 2)
    commit_total_gb = round(swap.total / (1024**3), 2)

    try:
        pi = _PERFORMANCE_INFORMATION()
        pi.cb = ctypes.sizeof(pi)
        if ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(pi), pi.cb):
            page = pi.PageSize
            sys_cache_bytes = pi.SystemCache * page
            cached_gb = round(sys_cache_bytes / (1024**3), 2)
            phys_avail_bytes = pi.PhysicalAvailable * page
            free_gb = round(max(0.0, (phys_avail_bytes - sys_cache_bytes * 0.4)) / (1024**3), 2)
            commit_used_gb = round((pi.CommitTotal * page) / (1024**3), 2)
            commit_total_gb = round((pi.CommitLimit * page) / (1024**3), 2)
    except Exception:
        pass

    return {
        "total_gb": total_gb,
        "used_gb": used_gb,
        "available_gb": available_gb,
        "cached_gb": cached_gb,
        "free_gb": free_gb,
        "percent": round(float(vm.percent), 1),
        "commit_used_gb": commit_used_gb,
        "commit_total_gb": commit_total_gb,
        "swap_percent": round(float(swap.percent), 1),
    }


def purge_standby_list(low_priority_only: bool = False, dry_run: bool = False) -> tuple[bool, str]:
    """Purge Windows Standby Memory List via NtSetSystemInformation (requires Admin)."""
    if dry_run:
        kind = "Low-Priority Standby List" if low_priority_only else "Standby Memory List"
        return True, f"[DRY-RUN] Would purge Windows {kind}."

    if not _enable_privilege("SeProfileSingleProcessPrivilege"):
        return False, "Standby list purge memerlukan hak Administrator (klik Elevate Admin)."

    cmd = ctypes.c_int(_MEMORY_PURGE_LOW_PRIORITY_STANDBY_LIST if low_priority_only else _MEMORY_PURGE_STANDBY_LIST)
    ntstatus = ctypes.windll.ntdll.NtSetSystemInformation(
        _SYSTEM_MEMORY_LIST_INFORMATION,
        ctypes.byref(cmd),
        ctypes.sizeof(cmd),
    )
    if ntstatus == 0:
        return True, "Standby Memory List berhasil dibersihkan."
    return False, f"NtSetSystemInformation status=0x{ntstatus & 0xFFFFFFFF:08X} (butuh hak Administrator)."


def flush_system_file_cache(dry_run: bool = False) -> tuple[bool, str]:
    """Flush Windows System File Cache working set via SetSystemFileCacheSize."""
    if dry_run:
        return True, "[DRY-RUN] Would flush Windows System File Cache."

    if not _enable_privilege("SeIncreaseQuotaPrivilege"):
        return False, "System File Cache flush memerlukan hak Administrator."

    ok = ctypes.windll.kernel32.SetSystemFileCacheSize(ctypes.c_size_t(-1), ctypes.c_size_t(-1), 0)
    if ok:
        return True, "System File Cache berhasil di-flush."
    return False, "System File Cache flush dilewati (akses terbatas)."


def trim_single_process(pid: int, dry_run: bool = False) -> tuple[bool, str]:
    """Trim working-set RAM of a single running process without closing it."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        before_mb = proc.memory_info().rss / (1024 * 1024)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False, f"Proses PID {pid} tidak dapat diakses."

    if dry_run:
        return True, f"[DRY-RUN] Would trim RAM for {name} (PID {pid}, currently {before_mb:.1f} MB)."

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_SET_QUOTA = 0x0100
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, int(pid))
    if not handle:
        return False, f"Akses ditolak untuk trim {name} (coba Elevate Admin)."
    try:
        ok = bool(ctypes.windll.psapi.EmptyWorkingSet(handle))
    finally:
        kernel32.CloseHandle(handle)

    if not ok:
        return False, f"Gagal trim working set untuk {name}."

    try:
        after_mb = psutil.Process(pid).memory_info().rss / (1024 * 1024)
        saved = max(0.0, before_mb - after_mb)
        return True, f"Trimmed {name}: {before_mb:.1f} MB -> {after_mb:.1f} MB (hemat {saved:.1f} MB)."
    except Exception:
        return True, f"Trimmed working set untuk {name}."


def clean_ram_deep(
    purge_standby: bool = True,
    trim_working_sets: bool = True,
    flush_file_cache: bool = True,
    dry_run: bool = False,
    log_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute full deep RAM cleanup and report before/after available RAM."""
    def log(msg: str) -> None:
        if log_cb:
            log_cb(msg)

    before_avail_mb = round(psutil.virtual_memory().available / (1024 * 1024), 1)
    trimmed_count = 0
    standby_ok = False
    cache_ok = False

    if trim_working_sets:
        trimmed_count, _ = trim_ram_working_sets(dry_run=dry_run, log_cb=log)

    if flush_file_cache:
        cache_ok, c_msg = flush_system_file_cache(dry_run=dry_run)
        log(c_msg)

    if purge_standby:
        standby_ok, s_msg = purge_standby_list(low_priority_only=False, dry_run=dry_run)
        log(s_msg)

    after_avail_mb = round(psutil.virtual_memory().available / (1024 * 1024), 1)
    freed_mb = 0.0 if dry_run else round(max(0.0, after_avail_mb - before_avail_mb), 1)
    admin_ok = is_admin()

    summary = (
        f"[DRY-RUN] Simulasi Deep RAM Clean (~{trimmed_count} proses)."
        if dry_run
        else f"RAM dibersihkan: +{freed_mb:.0f} MB lega ({trimmed_count} proses di-trim"
        + (", Standby Cache dibersihkan)." if standby_ok else ").")
    )
    log(summary)
    return {
        "before_avail_mb": before_avail_mb,
        "after_avail_mb": after_avail_mb,
        "freed_mb": freed_mb,
        "processes_trimmed": trimmed_count,
        "standby_purged": standby_ok,
        "file_cache_flushed": cache_ok,
        "is_admin": admin_ok,
        "summary": summary,
    }
