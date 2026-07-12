#!/usr/bin/env python3
"""Run a disposable clean-install, boot-probe, and rollback validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(command, text=True, capture_output=True, env=env)
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def extract(archive: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise RuntimeError("unsafe archive member")
        zf.extractall(destination)
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("invalid release archive root")
    return roots[0]


def build_authority(root: Path) -> Path:
    policy = root / "Specification Layer" / "HKP_ACTION_POLICY_STATE_v1.0.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        json.dumps({"policy_id": "HKP-POL-001", "schema_version": "1.0", "status": "APPROVED_ENFORCED"}) + "\n",
        encoding="utf-8",
    )
    sources = []
    for index in range(33):
        relative = Path("validation-fixture") / f"authority-{index:02d}.txt"
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"HermesOS disposable authority fixture {index}\n", encoding="utf-8")
        sources.append({"path": relative.as_posix(), "sha256": digest(target), "category": "validation_fixture"})
    manifest = {
        "manifest_id": "HKP-INT-006",
        "schema_version": "1.0",
        "baseline_reference": "disposable-validation-only",
        "algorithm": "SHA-256",
        "sources": sources,
    }
    (root / "HKP_INTEGRITY_MANIFEST_v6.0.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return root


def require(result: dict[str, object], phase: str) -> None:
    if result["returncode"] != 0:
        raise RuntimeError(f"{phase} failed: {result}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result: dict[str, object] = {"production_secrets_required": False, "live_target": False}
    try:
        if args.out.exists():
            shutil.rmtree(args.out)
        args.out.mkdir(parents=True)
        release = extract(args.archive, args.out / "release")
        runtime = args.out / "runtime"
        clone = run(["git", "clone", "--no-local", str(args.baseline), str(runtime)])
        result["baseline_clone"] = clone
        require(clone, "baseline clone")
        authority = build_authority(args.out / "authority")
        home = args.out / "hermes-home"
        workspace = args.out / "workspace"
        evidence = args.out / "evidence"
        bundle = release / "source_bundle" / "HERMESOS_GENESIS_SOURCE_BUNDLE_v0.2"
        config = {
            "GENESIS_PACKAGE_ROOT": str(bundle),
            "HKP_CANONICAL_ROOT": str(authority),
            "HKP_EVIDENCE_ROOT": str(evidence),
            "HKP_POLICY_ROOT": str(authority / "Specification Layer"),
            "HERMES_HOME": str(home),
            "HERMES_PROFILE_ROOT": str(home / "profiles"),
            "HERMES_RUNTIME_ROOT": str(runtime),
            "PROJECT_WORKSPACE_ROOT": str(workspace),
            "LIVE_TARGET": False,
            "secret_references": {
                "OPENROUTER_API_KEY": "env:OPENROUTER_API_KEY",
                "TELEGRAM_BOT_TOKEN_ASSISTANT": "env:TELEGRAM_BOT_TOKEN_ASSISTANT",
            },
        }
        config_path = args.out / "bindings.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        engine = release / "bootstrap" / "bootstrap_engine" / "genesis_bootstrap_v2.py"
        for mode in ("PREPARE", "APPLY"):
            phase = run([sys.executable, str(engine), mode, "--config", str(config_path), "--disposable-target"])
            result[mode.lower()] = phase
            require(phase, mode)
        probe_env = os.environ.copy()
        probe_env["HKP_AUTHORITY_ROOT"] = str(authority)
        probe_env["HERMES_HOME"] = str(home)
        probe = run([sys.executable, str(home / "scripts" / "hkp_boot_probe.py")], env=probe_env)
        result["boot_probe"] = probe
        require(probe, "boot probe")
        rollback = run([sys.executable, str(engine), "ROLLBACK", "--config", str(config_path), "--disposable-target"])
        result["rollback"] = rollback
        require(rollback, "rollback")
        status = run(["git", "-C", str(runtime), "status", "--porcelain=v1"])
        result["target_status"] = status
        require(status, "target status")
        state_file = workspace / "state" / "bootstrap_state_v2.json"
        state = json.loads(state_file.read_text(encoding="utf-8"))
        target_clean = not status["stdout"].strip()
        support_clean = not (home / "scripts" / "hkp_boot_probe.py").exists() and not (home / "profiles" / "hermesos").exists()
        state_clean = "active_snapshot" not in state
        result["final_target_clean"] = target_clean and support_clean and state_clean
        if not result["final_target_clean"]:
            raise RuntimeError("rollback did not restore the disposable target cleanly")
        result["result"] = "PASS"
    except Exception as exc:
        result["result"] = "FAIL"
        result["error"] = str(exc)
    (args.out / "clean_install_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": result["result"], "evidence": str(args.out / "clean_install_result.json")}))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
