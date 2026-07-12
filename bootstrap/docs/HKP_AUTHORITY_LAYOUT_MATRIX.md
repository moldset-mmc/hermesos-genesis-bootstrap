# HKP Authority Layout Reconciliation

**Scope:** isolated implementation workspace only. Canonical HKP and Source Bundle originals were not changed.

| Component | Expected root | Expected files / manifest | Required subpaths | Environment variables | Fallback | Failure behavior | Classification | Source reference |
|---|---|---|---|---|---|---|---|---|
| `hkp_boot_probe.py` | `HKP_AUTHORITY_ROOT` | `HKP_INTEGRITY_MANIFEST_v6.0.json`; ID `HKP-INT-006`; 33 sources | paths supplied by manifest | `HKP_AUTHORITY_ROOT`, `HERMES_HOME` | HERMES_HOME defaults to platform path; no HKP root fallback | exits 1; writes `DEGRADED` boot state | EXPECTED | Source Bundle `scripts/hkp_boot_probe.py` |
| corrected `governance_status.py` | `HKP_AUTHORITY_ROOT` | `HKP_INTEGRITY_MANIFEST_v6.0.json`; ID `HKP-INT-006`; schema `1.0` | `Specification Layer/HKP_ACTION_POLICY_STATE_v1.0.json` | `HKP_AUTHORITY_ROOT`, `HERMES_HOME` | Hermes home helper/default for runtime state only | integrity false / status fail closed | STALE_IMPLEMENTATION corrected in implementation package | Source Bundle `gateway/governance_status.py`; `E:/HKP/DOCUMENT_REGISTRY.md`; RC2.6 baseline |
| `hkp_policy_gate.py` | `HKP_AUTHORITY_ROOT` | `HKP_ACTION_POLICY_STATE_v1.0.json` | `Specification Layer/HKP_ACTION_POLICY_STATE_v1.0.json` | `HKP_AUTHORITY_ROOT` | none | invalid gate, side-effect denial | EXPECTED | Source Bundle `agent/hkp_policy_gate.py` |
| Gateway template | `HERMES_HOME` for probe; `HKP_AUTHORITY_ROOT` passed to probe | `<HERMES_HOME>/scripts/hkp_boot_probe.py` | `<HERMES_HOME>/scripts` | `HERMES_HOME`, `HKP_AUTHORITY_ROOT`, `VENV_PATH` | none | starts gateway in declared degraded state when probe fails | HOST_BINDING | Source Bundle `Hermes_Gateway.cmd.template` |
| Host bindings | owner-provided authority root | current authoritative manifest v6.0 | policy root below authority root | all six required bindings plus `HERMES_HOME` | none | engine blocks absent binding | HOST_BINDING | DP-09; implementation binding template |
| Minimum governance corpus | package-local dependency corpus | contains byte-identical `HKP_INTEGRITY_MANIFEST_v6.0.json` | does **not** contain all 33 manifest-referenced artifacts | none | none | cannot be promoted to authority root | EXPECTED BOUNDARY | Source Bundle `minimum_corpus`; DP-08 / discrepancies D-03 |
| Owner-bound authoritative HKP root | owner-provided canonical root | current `HKP_INTEGRITY_MANIFEST_v6.0.json`, `HKP-INT-006`, 33 sources | manifest-defined + policy subpath | `HKP_AUTHORITY_ROOT`, `HKP_POLICY_ROOT` | none | boot probe fails closed if missing/mismatch | EXPECTED | `E:/HKP/HKP_INTEGRITY_MANIFEST_v6.0.json`; `HKP_PRODUCTION_BASELINE_RC2_6.md` |

## Manifest-version finding

| Observation | Evidence | Classification |
|---|---|---|
| `HKP_INTEGRITY_MANIFEST_v1.3.json` exists in the authoritative root; its ID is `HKP-INT-004`, schema `1.3`, baseline RC2.1 and 18 sources. | Opened `E:/HKP/HKP_INTEGRITY_MANIFEST_v1.3.json` | LEGACY_COMPATIBILITY |
| `HKP_INTEGRITY_MANIFEST_v6.0.json` exists in the authoritative root and is byte-identical to the Source Bundle minimum-corpus copy; its ID is `HKP-INT-006`, schema `1.0`, baseline RC2.6 and 33 sources. | SHA-256 `964fd2e...d4ded7aa`; opened v6.0 files | EXPECTED |
| Registry identifies HKP-INT-006/v6.0 as successor to HKP-INT-005 and RC2.6 baseline calls it the integrity manifest. | Opened `E:/HKP/DOCUMENT_REGISTRY.md` and `Operating Layer/HKP_PRODUCTION_BASELINE_RC2_6.md` | EXPECTED |
| Source Bundle `governance_status.py` hardcodes v1.3/HKP-INT-004 while boot probe and current authority expect v6.0/HKP-INT-006. | Opened component sources and authority files | STALE_IMPLEMENTATION |

## Decision

`HKP_AUTHORITY_ROOT` is compatible with the current v6.0/RC2.6 chain only after the implementation-local correction replaces the stale governance-status expectation. Source Bundle originals remain evidence and were not modified.

The legacy v1.3 file is present, but it is not the current authoritative integrity anchor. No compatibility mapping is needed for the bootstrap v0.1 current-chain path; retaining a v1.3 requirement would be stale implementation behavior.

**Disposition:** `HKP AUTHORITY LAYOUT = COMPATIBLE (after implementation-local stale-component correction)`.

## Open boundaries

This is layout/source compatibility only. It does not prove boot-probe execution, gateway startup, runtime enforcement, isolation, or readiness.

The gateway template contains a separate variable naming defect: it declares `VENV_PATH` but invokes `%VIRTUAL_ENV%`. The template assigns `VIRTUAL_ENV=%%VENV_PATH%%`, so the invocation resolves after substitution; classification: `EXPECTED TEMPLATE BINDING`, not a blocker.

No `SOURCE_BUNDLE_CORRECTION_REQUIRED` record is created: the Source Bundle accurately preserves factual source material and documents its source-only status. The correction is required in the implementation overlay, not in the immutable source material.
'}【อ่านข้อความเต็ม to=functions.write_file  天天中彩票软件 天天中彩票官方  彩神争霸破解្យឹန်不中返json ನಂತರ출장샵user to=functions.read_file  大发彩票官网 盈立analysis  北京赛车女郎{