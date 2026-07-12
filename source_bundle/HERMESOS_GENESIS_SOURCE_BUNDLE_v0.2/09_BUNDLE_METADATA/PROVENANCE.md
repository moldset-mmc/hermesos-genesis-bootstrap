# Provenance — HermesOS Genesis Source Bundle v0.2

## Contract source
- Design contract: `03_GENESIS_DESIGN_PACK/HERMESOS_GENESIS_DESIGN_PACK_v0.1/`
- Inventory source: `01_SOURCE_INVENTORY/HERMESOS_SOURCE_INVENTORY_v0.1/`
- Analysis source: `02_GAP_ANALYSIS/HERMESOS_GENESIS_FOUNDATION_CROSSWALK_v0.1/`

## Upstream baseline (documented source evidence)
| Property | Value |
|---|---|
| Repository | `https://github.com/NousResearch/hermes-agent.git` |
| Branch | `main` |
| Pinned commit | `cd124ad1f` |
| pip package | `hermes-agent == 0.18.0` |
| Python | `>= 3.11` |

Baseline values are carried from Source Inventory `01_UPSTREAM_RUNTIME_BASELINE.md`. This assembly did not fetch, update, or alter upstream source.

## RC v0.1 overlay integration

RC v0.1 retains its original `gateway/governance_status.py` source record and
the `KEEP_AS_IMPLEMENTATION_OVERLAY` disposition for historical auditability.
For this next baseline, the corrected HKP-INT-006 / schema `1.0`
implementation is included directly at
`03_NEW_RUNTIME_FILES/gateway/governance_status.py`. Bootstrap APPLY uses that
integrated source and has no runtime overlay step.

## Extraction boundaries
- Profile artifacts came from the active `hermesos` profile and were cleaned of deployment bindings where detected.
- HKP documents are a **minimum dependency subset** copied for provenance and future bootstrap; the owner must provide the complete authoritative corpus required by HKP-INT-006.
- Runtime new files were copied as source material only. No patch was applied and no runtime was modified.
- The patch derives from the locally observed modifications recorded in Source Inventory; it covers 15 tracked upstream paths.

## Integrity and evidence
`SHASUMS.sha256` is generated after all package files except itself are finalized. Validation state is source-only; see `08_VALIDATION/`.
