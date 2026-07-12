# Discrepancies against Design Pack

## D-01 — Runtime enforcement implementation contains a host-specific source divergence
**Contract:** DP-09 requires no hardcoded host paths in portable payload.

**Observed source:** `tool_preflight.py`, `gateway/governance_status.py`, `hkp_boot_probe.py`, and an approval-service comment contained current-host default paths.

**Bundle treatment:** Source copies were parameterized to use `HKP_AUTHORITY_ROOT`, `HKP_EVIDENCE_BASE`, `HERMES_HOME`, or platform defaults. The original current runtime was not changed.

**Status:** DOCUMENTED; portable payload scan passes.

## D-02 — New-runtime-file count terminology is inconsistent in source records
**Contract/source wording:** Design Pack and Source Inventory state “13 new” runtime files/components.

**Observed physical source:** 11 `agent/` files + 1 `gateway/` file + 1 `hkp/` package component represented by 9 Python modules. Additionally, boot probe is validation source, not counted as a runtime-enforcement component.

**Bundle classification:** 13 runtime components represented by 21 physical runtime Python files; 1 separate boot-probe validation file. No architecture change is implied.

**Status:** DOCUMENTED; count is transparent rather than normalized by assumption.

## D-03 — HKP corpus is deliberately minimum, not full canonical authority root
**Contract:** DP-08 Phase 6 requires the full 33 canonical artifacts at deployment.

**Bundle content:** 11 dependency documents, including integrity manifest, Constitution parts, Foundation Index, GENESIS_000 and action-policy documents.

**Status:** EXPECTED BOUNDARY. The full corpus must be owner-provided/deployed separately and verified by boot probe. This bundle does not copy or modify canonical authority.

## D-04 — Patch application check unavailable in this assembly environment
**Expected:** DP-12 requires a known compatible source baseline before applying patches.

**Observed:** the local `hermes-agent/.git` metadata was not usable for a fresh `git archive`/`apply --check` validation at the end of assembly.

**Status:** SOURCE BUNDLE NOT BLOCKED. The patch was generated earlier from the recorded 15-file diff. A live-runtime dry run was not performed because this stage must not alter the active runtime; a disposable full-copy round-trip validation exceeded the execution time limit. Actual clean-baseline patch applicability is deferred to the Implementation stage and must gate patch application.
