#!/usr/bin/env python3
"""Read-only Source Bundle verification for HermesOS Genesis Bootstrap v0.1."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "hermesos.genesis.evidence.v0.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report(bundle: Path) -> dict[str, Any]:
    checksum_file = bundle / "09_BUNDLE_METADATA" / "SHASUMS.sha256"
    manifest = bundle / "manifest.yaml"
    checksum_problems: list[dict[str, str]] = []
    entries = 0
    for line_number, line in enumerate(checksum_file.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64}) \*\./(.+)", line)
        if not match:
            checksum_problems.append({"line": str(line_number), "error": "invalid checksum record"})
            continue
        expected, relative = match.groups()
        target = bundle / relative
        entries += 1
        if not target.is_file():
            checksum_problems.append({"path": relative, "error": "missing file"})
        elif sha256(target) != expected:
            checksum_problems.append({"path": relative, "error": "SHA-256 mismatch"})

    secret_rules = {
        "openai_like": re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}"),
        "github_pat": re.compile(r"(?<![A-Za-z0-9_-])gh[pousr]_[A-Za-z0-9_]{20,}"),
        "telegram_token": re.compile(r"(?<!\d)\d{8,12}:[A-Za-z0-9_-]{25,}"),
        "generic_assignment": re.compile(
            r"(?i)(?:api[_-]?key|token|password|secret)\s*[:=]\s*[\"']?"
            r"(?!\$\{|<|YOUR_|CHANGEME|REDACTED|PLACEHOLDER)[A-Za-z0-9+/=_-]{16,}"
        ),
    }
    secret_hits: list[dict[str, Any]] = []
    absolute_path_hits: list[dict[str, Any]] = []
    path_rules = [
        re.compile(r"(?i)[A-Z]:\\Users\\"),
        re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^\s\"']+"),
    ]
    exclusions = {"001_all_upstream_modifications.patch", "PROVENANCE.md"}
    for item in bundle.rglob("*"):
        if not item.is_file() or item.name in exclusions:
            continue
        try:
            content = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = item.relative_to(bundle).as_posix()
        for rule_name, rule in secret_rules.items():
            count = len(rule.findall(content))
            if count:
                secret_hits.append({"path": relative, "rule": rule_name, "count": count})
        path_count = sum(len(rule.findall(content)) for rule in path_rules)
        if path_count:
            absolute_path_hits.append({"path": relative, "count": path_count})

    result = "PASS" if manifest.is_file() and not checksum_problems and not secret_hits and not absolute_path_hits else "FAIL"
    return {
        "schema": SCHEMA,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "phase": "B_VERIFY_SOURCE_BUNDLE",
        "target": str(bundle),
        "inputs": {"manifest": str(manifest), "checksums": str(checksum_file)},
        "checks": {
            "manifest_present": manifest.is_file(),
            "sha256_entries": entries,
            "sha256_failures": checksum_problems,
            "real_secret_candidates": secret_hits,
            "portable_path_findings": absolute_path_hits,
        },
        "action": "read_only_verify",
        "result": result,
        "verification_level": "SOURCE_VERIFIED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    outcome = report(args.bundle)
    args.evidence_root.mkdir(parents=True, exist_ok=True)
    json_path = args.evidence_root / "phase_b_source_bundle_verification.json"
    md_path = args.evidence_root / "phase_b_source_bundle_verification.md"
    json_path.write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    checks = outcome["checks"]
    md_path.write_text(
        "\n".join(
            [
                "# Phase B — Source Bundle Verification",
                "",
                f"- Timestamp: `{outcome['timestamp_utc']}`",
                f"- Target: `{outcome['target']}`",
                f"- SHA-256 entries: `{checks['sha256_entries']}`",
                f"- SHA-256 failures: `{len(checks['sha256_failures'])}`",
                f"- Real-secret candidates: `{len(checks['real_secret_candidates'])}`",
                f"- Portable payload absolute-path findings: `{len(checks['portable_path_findings'])}`",
                f"- Result: **{outcome['result']}**",
                f"- Verification level: `{outcome['verification_level']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"result": outcome["result"], "evidence": str(json_path)}, ensure_ascii=False))
    return 0 if outcome["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
