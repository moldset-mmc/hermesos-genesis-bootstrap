# HermesOS Genesis Bootstrap

HermesOS Genesis Bootstrap is a reproducible bootstrap package for transforming a compatible clean Hermes Agent baseline into a separately provisioned HermesOS profile with HKP governance binding, runtime enforcement staging, boot validation, rollback support, and evidence generation.

This repository candidate preserves the RC v0.1 source, design, validation, and release provenance while separating source repository content from release artifacts, host-specific bindings, secrets, and generated runtime state.

## Supported Baseline

- Hermes Agent: `0.18.0`
- Upstream commit: `cd124ad1fae574dcdab8124924f84201d65277da`
- Python: `>=3.11`

## Repository Layout

- `bootstrap/`: approval-safe bootstrap engine, manifests, runtime corrections, and host binding templates.
- `source_bundle/`: source bundle originals, patch, minimum corpus, profile identity payload, validation metadata, and provenance.
- `design/`: normative design pack.
- `tests/`: repository tests for approval-safe behavior and package contracts.
- `validation/`: validation summary and future validation material.
- `release/`: RC release docs and checksum manifests.
- `evidence/examples/`: non-secret release evidence examples.
- `docs/`: compatibility, limitations, handoff, and repository guidance.

## Execution Boundary

The sole approval-safe executable engine is:

```bash
python bootstrap/bootstrap_engine/genesis_bootstrap_v2.py INSPECT --config host-bindings.json
```

`bootstrap/bootstrap_engine/genesis_bootstrap.py` is compatibility-only and forwards to v2.

`APPLY` refuses live targets. Disposable apply requires `--disposable-target` and a passing atomic preflight. Live publication, live mutation, credential injection, gateway restart, and GitHub publication all require separate explicit approval.

## Quick Verification

```bash
python -m pytest tests -q
```

Checksum/package verification is expected to run against the sealed release artifact or the source bundle manifest before release packaging.

## Licensing And Attribution

HermesOS Genesis is MIT-licensed. Hermes Agent is an upstream project of Nous
Research; this repository preserves applicable upstream MIT notices and does
not claim ownership of upstream code. See `LICENSE` and `NOTICE`.

## Current Readiness

This is a repository candidate, not a published release. Known limitations remain documented in `docs/03_KNOWN_LIMITATIONS.md`.
