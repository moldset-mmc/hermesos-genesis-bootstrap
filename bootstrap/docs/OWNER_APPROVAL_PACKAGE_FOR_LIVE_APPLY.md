# Owner Approval Package for Live Apply — Re-review v0.2

## Status

**READY FOR OWNER RE-REVIEW.** This document is evidence for a future decision only. It grants no live mutation authority.

## Corrected approval controls

| Control | Evidence-backed result |
|---|---|
| Exact 15 mutation paths | PASS — parser preserves `agent/...` paths from non-prefixed patch headers; no `ent/...` truncation |
| Atomic pre-apply preflight | PASS — baseline, git status, patch paths, sources, collisions, overlay, boot probe destination, bindings, secret references and snapshot location checked before APPLY |
| Zero mutation on failed preflight | PASS — dirty disposable target returned `BLOCKED`; no APPLY executed |
| Safe rollback | PASS — snapshot captures pre-apply HEAD/status, all 15 modified files, created files and runtime-support/profile artifacts; deterministic restore tested without `git reset --hard` |
| Live target inspection | PASS — read-only `LIVE_TARGET_INSPECTION` produces exact target identity, head, version, status, expected paths, collisions and compatibility |
| Secret safety | PASS — evidence serializes redacted/allowlisted config only; secret references must be `env:` or `vault:` and values are never serialized |
| Approval integrity | PASS — `APPROVAL_PACKAGE_SHASUMS.sha256` covers approval-relevant artifacts and was verified |
| Validation contract | PASS — implemented checks and non-executable live checks are explicitly separated in `docs/VALIDATION_CONTRACT_ALIGNMENT.md` |

## Evidence set

- `evidence/approval_package_re_review.json`
- `evidence/pre_apply_atomic_preflight.json`
- `evidence/live_target_inspection.json`
- `evidence/SOURCE_BUNDLE_CORRECTION_REQUIRED.md`
- `docs/VALIDATION_CONTRACT_ALIGNMENT.md`
- `APPROVAL_PACKAGE_SHASUMS.sha256`

## Exact prospective live scope

A future owner-approved operation must still identify a concrete live target and rerun `LIVE_TARGET_INSPECTION`, `PLAN` and `PREFLIGHT` on that target. No prior disposable output substitutes for this.

Only after explicit approval may a future operator modify exactly the 15 upstream paths from `LIVE_TARGET_MUTATION_PLAN.json`, add manifest-listed runtime files, install the boot probe at `<HERMES_HOME>/scripts/hkp_boot_probe.py`, and apply the documented implementation overlay.

## Required preconditions

1. Explicit approval naming the exact runtime target and generated `LIVE_TARGET_MUTATION_PLAN.json`.
2. Current target passes atomic preflight with an empty git status.
3. Full owner-bound HKP root validates against HKP-INT-006.
4. Required secret **references** exist; values are not disclosed to the plan/evidence.
5. Snapshot storage is writable and rollback operator is confirmed.
6. Gateway restart and external connectivity have separate approval.

## Source Bundle discrepancy

`03_NEW_RUNTIME_FILES/gateway/governance_status.py` remains classified as `STALE_IMPLEMENTATION` because it expects legacy v1.3/HKP-INT-004.

Current disposition: **`KEEP_AS_IMPLEMENTATION_OVERLAY`**.

Future choices remain `SOURCE_BUNDLE_REVISION` or `RELEASE_BASELINE_INTEGRATION`. Source Bundle originals were not changed.

## Non-claims

- LIVE APPLY: **NOT EXECUTED**
- LIVE RUNTIME MODIFIED: **NO**
- LIVE VERIFIED: **NO**
- ISOLATION VERIFIED: **NO**
- READY: **NO**
