#!/usr/bin/env python3
"""
HKP Boot Probe — Runtime Conformance and Integrity Verification
================================================================
Phase 32 — RUNTIME CONFORMANCE AND BOOT ADAPTATION RELEASE

Verifies the active HKP control chain against HKP-INT-006 at startup.
Declares one of two runtime states:
  - HKP GOVERNED / VERIFIED
  - HKP DEGRADED / INTEGRITY FAILURE

This script is a non-canonical local boot-verification tool.
It does NOT modify any canonical HKP artifact.

Outputs:
  ~/AppData/Local/hermes/hkp_boot_state.json   — machine-readable state
  ~/AppData/Local/hermes/hkp_boot_evidence.log  — detailed evidence log

Exit codes:
  0 — HKP GOVERNED / VERIFIED
  1 — HKP DEGRADED / INTEGRITY FAILURE
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────
HKP_ROOT = os.environ.get("HKP_AUTHORITY_ROOT")
HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes")

if not HKP_ROOT:
    print("HKP_AUTHORITY_ROOT is required", file=sys.stderr)
    sys.exit(1)

MANIFEST_PATH = os.path.join(HKP_ROOT, "HKP_INTEGRITY_MANIFEST_v6.0.json")
STATE_OUTPUT = os.path.join(HERMES_HOME, "hkp_boot_state.json")
EVIDENCE_LOG = os.path.join(HERMES_HOME, "hkp_boot_evidence.log")

# ── Logging ───────────────────────────────────────────────────────────
def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(EVIDENCE_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (PermissionError, OSError):
        pass  # stdout already captured by shell redirect

def sha256_file(path):
    """Compute SHA-256 of a file. Returns hex digest or None on error."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, PermissionError, OSError) as e:
        log(f"  ERROR reading {path}: {e}")
        return None

# ── Main ──────────────────────────────────────────────────────────────
def main():
    log("=" * 72)
    log("HKP BOOT PROBE — Phase 32 Runtime Conformance Verification")
    log(f"HKP_ROOT: {HKP_ROOT}")
    log(f"Manifest: {MANIFEST_PATH}")
    log("=" * 72)

    # 1. Read manifest
    if not os.path.isfile(MANIFEST_PATH):
        log(f"FATAL: Manifest not found at {MANIFEST_PATH}")
        _write_state("DEGRADED", "MANIFEST_NOT_FOUND", [])
        return 1

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log(f"FATAL: Cannot parse manifest: {e}")
        _write_state("DEGRADED", "MANIFEST_PARSE_ERROR", [])
        return 1

    manifest_id = manifest.get("manifest_id", "UNKNOWN")
    log(f"Manifest: {manifest_id}")
    log(f"Baseline: {manifest.get('baseline_reference', 'UNKNOWN')}")
    log(f"Generated: {manifest.get('generated_at_utc', 'UNKNOWN')}")
    log(f"Algorithm: {manifest.get('algorithm', 'UNKNOWN')}")

    sources = manifest.get("sources", [])
    log(f"\nVerifying {len(sources)} canonical source(s)...\n")

    # 2. Verify each source
    failures = []
    verified_count = 0
    skipped_count = 0

    for src in sources:
        path = src["path"]
        expected = src["sha256"]
        category = src.get("category", "unknown")
        full_path = os.path.join(HKP_ROOT, path)

        if not os.path.isfile(full_path):
            log(f"  ❌ {path}  — FILE NOT FOUND")
            failures.append({"path": path, "reason": "FILE_NOT_FOUND", "expected_sha256": expected})
            continue

        actual = sha256_file(full_path)
        if actual is None:
            failures.append({"path": path, "reason": "READ_ERROR"})
            continue

        if actual == expected:
            log(f"  ✅ {path}  — SHA-256 MATCH")
            verified_count += 1
        else:
            log(f"  ❌ {path}  — SHA-256 MISMATCH")
            log(f"     Expected: {expected}")
            log(f"     Actual:   {actual}")
            failures.append({"path": path, "reason": "SHA256_MISMATCH",
                             "expected_sha256": expected, "actual_sha256": actual})

    # 3. Determine state
    total = len(sources)
    log(f"\n{'=' * 72}")
    log(f"Verified: {verified_count}/{total}  |  Failures: {len(failures)}  |  Skipped: {skipped_count}")

    if len(failures) == 0:
        state = "VERIFIED"
        state_label = "HKP GOVERNED / VERIFIED"
        reason = "All canonical artifacts match HKP-INT-006 manifest"
        exit_code = 0
        log(f"\n✅ {state_label}")
    else:
        state = "DEGRADED"
        state_label = "HKP DEGRADED / INTEGRITY FAILURE"
        failed_paths = [f["path"] for f in failures]
        reason = f"Integrity chain broken: {len(failures)} artifact(s) failed verification"
        exit_code = 1
        log(f"\n⚠️  {state_label}")
        log(f"Failed artifacts: {', '.join(failed_paths)}")

    # 4. Write state
    _write_state(state, reason, failures)

    log(f"\nState written to: {STATE_OUTPUT}")
    log(f"Evidence log: {EVIDENCE_LOG}")
    log("HKP BOOT PROBE COMPLETE")
    log("=" * 72)

    return exit_code


def _write_state(state, reason, failures):
    """Write machine-readable boot state JSON."""
    payload = {
        "hkp_state": state,
        "state_label": "HKP GOVERNED / VERIFIED" if state == "VERIFIED" else "HKP DEGRADED / INTEGRITY FAILURE",
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": "HKP-INT-006",
        "baseline": "HKP-BSL-006 / RC2.6",
        "algorithm": "SHA-256",
        "reason": reason,
        "failure_count": len(failures),
        "failures": failures,
        "probe": {
            "script": "hkp_boot_probe.py",
            "version": "1.0",
            "phase": "32"
        }
    }
    with open(STATE_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"UNEXPECTED ERROR: {e}")
        _write_state("DEGRADED", f"PROBE_ERROR: {e}", [])
        sys.exit(1)
