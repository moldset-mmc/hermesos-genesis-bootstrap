from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TEST_FILE = Path(__file__).resolve()
ROOT = TEST_FILE.parents[1] if (TEST_FILE.parents[1] / "bootstrap_engine").is_dir() else TEST_FILE.parents[2] / "bootstrap"
ENGINE = ROOT / "bootstrap_engine" / "genesis_bootstrap_v2.py"
MANIFEST = ROOT / "manifests" / "installation_manifest.json"


def test_installation_manifest_has_explicit_boundary():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["upstream"]["pinned_commit"].startswith("cd124ad1f")
    assert len(data["patch"]["affected_upstream_paths"]) == 15
    assert data["runtime_support"]["boot_probe"]["destination"] == "<HERMES_HOME>/scripts/hkp_boot_probe.py"
    assert data["runtime_support"]["boot_probe"]["deployment_class"] == "HERMES_HOME_RUNTIME_SUPPORT"
    assert data["governance_binding"]["authoritative_integrity_manifest"] == "HKP_INTEGRITY_MANIFEST_v6.0.json"
    assert data["governance_binding"]["bootstrap_minimum_corpus_is_not_authoritative_root"] is True
    assert data["runtime_source_mode"] == "INTEGRATED"


def test_engine_refuses_live_apply(tmp_path: Path):
    cfg = {
        "GENESIS_PACKAGE_ROOT": str(tmp_path),
        "HKP_CANONICAL_ROOT": str(tmp_path),
        "HKP_EVIDENCE_ROOT": str(tmp_path / "evidence"),
        "HKP_POLICY_ROOT": str(tmp_path),
        "HERMES_PROFILE_ROOT": str(tmp_path),
        "HERMES_RUNTIME_ROOT": str(tmp_path),
        "PROJECT_WORKSPACE_ROOT": str(tmp_path / "workspace"),
        "LIVE_TARGET": True,
    }
    config = tmp_path / "bindings.json"
    config.write_text(json.dumps(cfg), encoding="utf-8")
    result = subprocess.run([sys.executable, str(ENGINE), "APPLY", "--config", str(config), "--disposable-target"], text=True)
    assert result.returncode == 2
    evidence = next((tmp_path / "evidence" / "runtime").glob("*.json"))
    assert json.loads(evidence.read_text(encoding="utf-8"))["result"] == "BLOCKED"


def test_engine_exposes_all_required_modes():
    source = ENGINE.read_text(encoding="utf-8")
    for mode in ("INSPECT", "PLAN", "VALIDATE_PACKAGE", "PREPARE", "APPLY", "VALIDATE", "ROLLBACK", "STATUS"):
        assert mode in source
    assert "h/'scripts'/'hkp_boot_probe.py'" in source
    assert 'PLAN_LIVE' in source
