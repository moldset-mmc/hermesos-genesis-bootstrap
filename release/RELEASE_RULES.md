# Release Rules

## Source Repository

The source repository contains design materials, source bundle originals, bootstrap implementation, tests, docs, and example evidence. It must not contain host-specific secrets, generated rollback snapshots, caches, or live runtime state.

## Release Artifact

A release artifact is built from a clean source tree and includes only the files required for deterministic bootstrap review and execution. It must include checksum manifests and a sidecar SHA-256.

## Host-Specific Configuration

Host bindings are created from `bootstrap/config_templates/host-bindings.template.json`. Real bindings are local operator state and should not be committed unless explicitly sanitized as examples.

## Generated State

Runtime evidence, rollback snapshots, prepared payload workspaces, and bootstrap state are generated outputs. Store release-validation samples under `evidence/examples/` only after secret review.

