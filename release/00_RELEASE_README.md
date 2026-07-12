# HermesOS Genesis Bootstrap — Release Candidate v0.1

## Product and release

| Field | Value |
|---|---|
| Product | `HERMESOS_GENESIS_BOOTSTRAP` |
| Release | `RC v0.1` |
| Scope | Reproducible clean-install bootstrap package |
| Publication status | Not published |
| Live apply status | Not executed |

## Proven result

```text
CLEAN INSTALL BOOTSTRAP = PASS
REPRODUCIBLE FROM CLEAN OFFICIAL HERMES = YES
BOOT PROBE = PASS
ROLLBACK = PASS
LIVE CURRENT HERMES MODIFIED = NO
```

## Entrypoint

The sole approval-safe engine is:

```text
packages/HERMESOS_GENESIS_BOOTSTRAP_IMPLEMENTATION_v0.1/
bootstrap_engine/genesis_bootstrap_v2.py
```

`genesis_bootstrap.py` is compatibility-only and marked `LEGACY_NOT_FOR_EXECUTION`.

Read in order:

1. `01_RELEASE_MANIFEST.yaml`
2. `02_COMPATIBILITY.md`
3. `03_KNOWN_LIMITATIONS.md`
4. implementation `README.md`
5. `04_VALIDATION_SUMMARY.md`
6. `05_CODEX_HANDOFF.md`

## Included packages

- `packages/HERMESOS_GENESIS_DESIGN_PACK_v0.1/`
- `packages/HERMESOS_GENESIS_SOURCE_BUNDLE_v0.1/`
- `packages/HERMESOS_GENESIS_BOOTSTRAP_IMPLEMENTATION_v0.1/`

All checksums are in `checksums/`.

## Boundary

This RC does not authorize live mutation, Gateway restart, external service connection, credential injection, GitHub publication, or changes to Foundation, Design Pack, canonical HKP, or Source Bundle originals.

## Next stage

```text
CODEX ENGINEERING REVIEW
→ GITHUB REPOSITORY PREPARATION
→ RELEASE
```
