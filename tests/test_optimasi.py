"""Comprehensive offline & dry-run tests for Optimasi Windows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from optimasi.core.cleaner import clean_junk, scan_junk
from optimasi.core.executor import (
    HOSTS_BEGIN_MARKER,
    HOSTS_END_MARKER,
    TweakExecutor,
    apply_hosts_block,
    remove_hosts_block,
)
from optimasi.core.system_info import get_system_snapshot
from optimasi.main import main as cli_main
from optimasi.tweaks import ALL_TWEAKS, CATEGORIES, PRESETS, TWEAK_BY_ID, get_preset_tweaks, search_tweaks
from optimasi.tweaks.models import RiskLevel


def test_python_runtime_is_311() -> None:
    assert sys.version_info[:2] == (3, 11)


def test_tweaks_catalog_integrity() -> None:
    assert len(ALL_TWEAKS) >= 40
    ids = [t.id for t in ALL_TWEAKS]
    assert len(ids) == len(set(ids)), "Duplicate tweak IDs found"

    for t in ALL_TWEAKS:
        assert t.name.strip()
        assert t.category in CATEGORIES
        assert isinstance(t.risk, RiskLevel)
        assert len(t.apply_actions) > 0, f"Tweak {t.id} has no apply_actions"
        assert t.source.strip()


def test_presets_reference_valid_tweaks() -> None:
    assert len(PRESETS) == 3
    for preset in PRESETS:
        assert len(preset.tweak_ids) > 5
        for tid in preset.tweak_ids:
            assert tid in TWEAK_BY_ID, f"Preset {preset.id} references unknown tweak {tid}"
        resolved = get_preset_tweaks(preset.id)
        assert len(resolved) == len(preset.tweak_ids)


def test_search_tweaks() -> None:
    assert len(search_tweaks("")) == len(ALL_TWEAKS)
    assert any(t.id == "net_disable_nagle" for t in search_tweaks("nagle"))
    assert any(t.id == "priv_disable_ai_copilot" for t in search_tweaks("copilot"))


def test_executor_dry_run_all_tweaks() -> None:
    logs: list[str] = []
    executor = TweakExecutor(dry_run=True, log_cb=logs.append)
    result = executor.run_tweaks(ALL_TWEAKS, revert=False, session_label="PytestDryRunAll")
    assert result.failed == 0
    assert result.succeeded > 0
    assert result.session_file is None
    assert any("[DRY-RUN]" in line for line in logs)

    # Also test dry-run revert path
    rev_res = executor.run_tweaks(ALL_TWEAKS, revert=True, session_label="PytestDryRunRevert")
    assert rev_res.failed == 0


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

    # Re-applying should be idempotent (only one begin marker)
    apply_hosts_block(["telemetry.example.com", "ads.example.com"], hosts_path=hosts, dry_run=False)
    content2 = hosts.read_text(encoding="utf-8")
    assert content2.count(HOSTS_BEGIN_MARKER) == 1

    # Removing restores clean original content
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

    # Dry run keeps files intact
    dry_sum = clean_junk(["mock_temp"], categories_override=cats, dry_run=True)
    assert dry_sum.files_deleted == 2
    assert (junk_dir / "a.tmp").exists()

    # Live clean on isolated temp dir deletes files
    live_sum = clean_junk(["mock_temp"], categories_override=cats, dry_run=False)
    assert live_sum.files_deleted == 2
    assert live_sum.bytes_freed == 3072
    assert not (junk_dir / "a.tmp").exists()


def test_system_snapshot_structure() -> None:
    snap = get_system_snapshot()
    assert "os" in snap and "name" in snap["os"]
    assert snap["cpu"]["logical_cores"] >= 1
    assert snap["ram"]["total_gb"] > 0
    assert snap["disk_c"]["total_gb"] > 0
    assert snap["python_version"].startswith("3.11")


def test_cli_self_test_out(tmp_path: Path) -> None:
    out_file = tmp_path / "selftest.json"
    rc = cli_main(["--self-test-out", str(out_file)])
    assert rc == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["python_major_minor"] == [3, 11]
    assert data["dry_run_ok"] is True
    assert data["tk_assets_ok"] is True
    assert data["tweak_count"] == len(ALL_TWEAKS)
