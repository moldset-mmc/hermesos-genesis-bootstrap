# SOURCE_BUNDLE_CORRECTION_REQUIRED

## Finding

| Field | Value |
|---|---|
| Source Bundle component | `03_NEW_RUNTIME_FILES/gateway/governance_status.py` |
| Classification | `STALE_IMPLEMENTATION` |
| Observed expectation | `HKP_INTEGRITY_MANIFEST_v1.3.json`, `HKP-INT-004`, schema `1.3` |
| Current authoritative chain | `HKP_INTEGRITY_MANIFEST_v6.0.json`, `HKP-INT-006`, RC2.6, schema `1.0` |
| Evidence | `docs/HKP_AUTHORITY_LAYOUT_MATRIX.md`; `evidence/hkp_authority_layout_reconciliation.json` |
| Source Bundle action | **None. Source Bundle originals remain immutable.** |
| Current implementation disposition | `runtime_corrections/gateway/governance_status.py` overlay applied in disposable reconstruction |

## Current disposition

`KEEP_AS_IMPLEMENTATION_OVERLAY`

The implementation overlay is the active controlled correction for this package revision. This is not a silent change to the immutable Source Bundle.

## Future disposition required

Before release-baseline finalization, re-evaluate one of:

1. `KEEP_AS_IMPLEMENTATION_OVERLAY` — retain the documented overlay;
2. `SOURCE_BUNDLE_REVISION` — publish a new immutable Source Bundle revision;
3. `RELEASE_BASELINE_INTEGRATION` — integrate the correction into a new approved release baseline.

No canonical HKP artifact was changed. No live runtime was changed.
