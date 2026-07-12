# Codex Engineering Handoff

## What this project is

`HERMESOS_GENESIS_BOOTSTRAP` is a reproducible bootstrap package for constructing a HermesOS profile and HKP-enabled runtime from a clean compatible Hermes Agent baseline.

This RC is a sealed engineering review input. It is not a live-apply authorization and is not published.

## What is proven

```text
CLEAN INSTALL BOOTSTRAP = PASS
REPRODUCIBLE FROM CLEAN OFFICIAL HERMES = YES
BOOT PROBE = PASS
ROLLBACK = PASS
LIVE CURRENT HERMES MODIFIED = NO
```

Supported baseline:

```text
Hermes Agent 0.18.0
cd124ad1fae574dcdab8124924f84201d65277da
Python >=3.11
```

## Do not redesign without evidence

Codex must not silently change:

- Foundation or canonical HKP artifacts;
- approved Design Pack semantics;
- source-bundle originals;
- lifecycle boundaries;
- owner approval gates;
- secret model;
- HKP authority model;
- claimed validation results.

Architecture changes require explicit evidence and owner/ADR handling outside this RC task.

## Normative / implementation classification

| Class | Location |
|---|---|
| Normative contract | `packages/HERMESOS_GENESIS_DESIGN_PACK_v0.1/` |
| Clean source material | `packages/HERMESOS_GENESIS_SOURCE_BUNDLE_v0.1/` |
| Implementation | `packages/HERMESOS_GENESIS_BOOTSTRAP_IMPLEMENTATION_v0.1/` |
| Sole approval-safe engine | `bootstrap_engine/genesis_bootstrap_v2.py` |
| Legacy compatibility wrapper | `bootstrap_engine/genesis_bootstrap.py` — not for direct execution |
| Release evidence | `evidence/` |

## Open findings

- `gateway/governance_status.py` is classified `STALE_IMPLEMENTATION` in the Source Bundle and currently handled through `KEEP_AS_IMPLEMENTATION_OVERLAY`.
- External provider inference, Telegram/Gateway production connectivity, and live permissions/isolation are not validated by the clean-install test.
- Current local Hermes is an existing HKP-enabled reference implementation with separate convergence findings; do not apply the bootstrap patch to it as though it were clean upstream.

## Expected Codex tasks

1. Repository normalization.
2. Code review.
3. Security review.
4. Test and CI construction.
5. Packaging review.
6. Git hygiene.
7. Release automation.
8. GitHub publication preparation.

Codex should verify checksums before work, preserve the package boundary, create explicit patches/commits, and report any discrepancy instead of normalizing it silently.

## Non-goals

- No GitHub publication.
- No live mutation.
- No credential injection.
- No Foundation/Design Pack redesign.
- No change to canonical HKP.

## Suggested first command

Verify `checksums/RC_SHASUMS.sha256`, then inspect `01_RELEASE_MANIFEST.yaml`, `04_VALIDATION_SUMMARY.md`, and the implementation README.