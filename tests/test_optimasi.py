"""Comprehensive offline & dry-run tests for Optimasi Windows v2.0.0."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from optimasi import APP_VERSION
from optimasi.core.booster import GameBooster, set_laptop_thermal_mode
from optimasi.core.cleaner import clean_junk, scan_junk
from optimasi.core.executor import (
    HOSTS_BEGIN_MARKER,
    HOSTS_END_MARKER,
    TweakExecutor,
    apply_hosts_block,
    remove_hosts_block,
)
from optimasi.core.health_score import evaluate_optimization_score
from optimasi.core.system_info import get_system_snapshot, get_top_processes, terminate_process
from optimasi.core.updater import (
    is_newer_version,
    launch_update_installer,
    parse_semver,
    select_release_asset,
)
from optimasi.main import main as cli_main
from optimasi.tweaks import ALL_TWEAKS, CATEGORIES, PRESETS, TWEAK_BY_ID, get_preset_tweaks, search_tweaks
from optimasi.tweaks.models import RiskLevel


def test_python_runtime_is_311() -> None:
    assert sys.version_info[:2] == (3, 11)


def test_tweaks_catalog_integrity() -> None:
    assert len(ALL_TWEAKS) >= 55
    ids = [t.id for t in ALL_TWEAKS]
    assert len(ids) == len(set(ids)), "Duplicate tweak IDs found"

    for t in ALL_TWEAKS:
        assert t.name.strip()
        assert t.category in CATEGORIES
        assert isinstance(t.risk, RiskLevel)
        assert len(t.apply_actions) > 0, f"Tweak {t.id} has no apply_actions"
        assert t.source.strip()


def test_presets_include_laptop_profiles() -> None:
    assert len(PRESETS) == 4
    preset_ids = {p.id for p in PRESETS}
    assert {"laptop_pro", "laptop_battery", "gaming_pro", "safe_daily"} == preset_ids

    for preset in PRESETS:
        assert len(preset.tweak_ids) > 5
        for tid in preset.tweak_ids:
            assert tid in TWEAK_BY_ID, f"Preset {preset.id} references unknown tweak {tid}"
        resolved = get_preset_tweaks(preset.id)
        assert len(resolved) == len(preset.tweak_ids)

    # Laptop Pro preset must NOT disable memory compression or hibernation
    laptop_ids = set(next(p for p in PRESETS if p.id == "laptop_pro").tweak_ids)
    assert "ram_disable_compression" not in laptop_ids
    assert "cpu_disable_hibernation" not in laptop_ids
    assert "cpu_laptop_ac_dc_smart" in laptop_ids


def test_search_tweaks() -> None:
    assert len(search_tweaks("")) == len(ALL_TWEAKS)
    assert any(t.id == "net_disable_nagle" for t in search_tweaks("nagle"))
    assert any(t.id == "priv_disable_ai_copilot" for t in search_tweaks("copilot"))
    assert any(t.id == "cpu_laptop_ac_dc_smart" for t in search_tweaks("laptop"))


def test_executor_dry_run_all_tweaks() -> None:
    logs: list[str] = []
    executor = TweakExecutor(dry_run=True, log_cb=logs.append)
    result = executor.run_tweaks(ALL_TWEAKS, revert=False, session_label="PytestDryRunAll")
    assert result.failed == 0
    assert result.succeeded > 0
    assert result.session_file is None
    assert any("[DRY-RUN]" in line for line in logs)

    rev_res = executor.run_tweaks(ALL_TWEAKS, revert=True, session_label="PytestDryRunRevert")
    assert rev_res.failed == 0


def test_health_score_structure() -> None:
    score = evaluate_optimization_score()
    assert 0 <= score["score"] <= 100
    assert score["grade"] in ("S", "A", "B", "C", "D")
    assert score["total_count"] == 8
    assert len(score["checks"]) == 8


def test_updater_semver_and_asset_selection(tmp_path: Path) -> None:
    assert parse_semver("v2.1.0") == (2, 1, 0)
    assert is_newer_version("v2.1.0", "2.0.0") is True
    assert is_newer_version("v2.0.0", "2.0.0") is False
    assert is_newer_version("v1.0.0", "2.0.0") is False

    assets = [
        {"name": "OptimasiWindows.exe", "browser_download_url": "https://example.com/portable.exe"},
        {"name": "OptimasiWindows-Setup-2.1.0.exe", "browser_download_url": "https://example.com/setup.exe"},
    ]
    chosen = select_release_asset(assets)
    assert chosen is not None
    assert chosen["name"] == "OptimasiWindows-Setup-2.1.0.exe"

    fake_setup = tmp_path / "OptimasiWindows-Setup-2.1.0.exe"
    ok, msg = launch_update_installer(fake_setup, is_installer=True, dry_run=True)
    assert ok and "[DRY-RUN]" in msg


def test_booster_and_thermal_dry_run() -> None:
    booster = GameBooster()
    res = booster.activate_boost(dry_run=True)
    assert res["active"] is True
    assert booster.active is True

    ok_r, _ = booster.restore_boost(dry_run=True)
    assert ok_r is True
    assert booster.active is False

    ok_t, msg_t = set_laptop_thermal_mode("cool_quiet", dry_run=True)
    assert ok_t and "[DRY-RUN]" in msg_t


def test_hosts_block_idempotent_and_revert(tmp_path: Path) -> None:
    hosts = tmp_path / "hosts"
    hosts.write_text("127.0.0.1 localhost\n", encoding="utf-8")

    ok, _ = apply_hosts_block(["telemetry.example.com", "ads.example.com"], hosts_path=hosts, dry_run=False)
    assert ok
    content1 = hosts.read_text(encoding="utf-8")
    assert "127.0.0.1 localhost" in content1
    assert HOSTS_BEGIN_MARKER in content1
    assert "0.0.0.0\ttelemetry.example.com" in content1
    assert HOSTS_END_MARKER in content1

    apply_hosts_block(["telemetry.example.com", "ads.example.com"], hosts_path=hosts, dry_run=False)
    content2 = hosts.read_text(encoding="utf-8")
    assert content2.count(HOSTS_BEGIN_MARKER) == 1

    ok_rem, _ = remove_hosts_block(hosts_path=hosts, dry_run=False)
    assert ok_rem
    content3 = hosts.read_text(encoding="utf-8")
    assert HOSTS_BEGIN_MARKER not in content3
    assert "127.0.0.1 localhost" in content3


def test_cleaner_scan_and_clean_isolated(tmp_path: Path) -> None:
    junk_dir = tmp_path / "temp_junk"
    junk_dir.mkdir()
    (junk_dir / "a.tmp").write_bytes(b"x" * 1024)
    sub = junk_dir / "nested"
    sub.mkdir()
    (sub / "b.log").write_bytes(b"y" * 2048)

    cats = [{"key": "mock_temp", "label": "Mock Temp", "description": "Test", "paths": [str(junk_dir)]}]
    stats = scan_junk(categories_override=cats)
    assert len(stats) == 1
    assert stats[0].file_count == 2
    assert stats[0].size_bytes == 3072

    dry_sum = clean_junk(["mock_temp"], categories_override=cats, dry_run=True)
    assert dry_sum.files_deleted == 2
    assert (junk_dir / "a.tmp").exists()

    live_sum = clean_junk(["mock_temp"], categories_override=cats, dry_run=False)
    assert live_sum.files_deleted == 2
    assert live_sum.bytes_freed == 3072
    assert not (junk_dir / "a.tmp").exists()


def test_system_snapshot_and_processes() -> None:
    snap = get_system_snapshot()
    assert "os" in snap and "name" in snap["os"]
    assert "is_laptop" in snap and "battery" in snap
    assert snap["cpu"]["logical_cores"] >= 1
    assert snap["ram"]["total_gb"] > 0
    assert snap["disk_c"]["total_gb"] > 0
    assert snap["python_version"].startswith("3.11")

    procs = get_top_processes(limit=5)
    assert len(procs) > 0
    ok_kill, _ = terminate_process(4, dry_run=False)
    assert ok_kill is False  # Protected System PID 4


def test_cli_self_test_out(tmp_path: Path) -> None:
    out_file = tmp_path / "selftest.json"
    rc = cli_main(["--self-test-out", str(out_file)])
    assert rc == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["app_version"] == APP_VERSION
    assert data["python_major_minor"] == [3, 11]
    assert data["dry_run_ok"] is True
    assert data["pyside6_ok"] is True
    assert data["updater_semver_ok"] is True
    assert data["tweak_count"] == len(ALL_TWEAKS)
