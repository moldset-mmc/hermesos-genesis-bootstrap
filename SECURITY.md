# Security Policy

## Supported Scope

This candidate covers HermesOS Genesis Bootstrap RC v0.1 preparation for source publication. It does not authorize live Hermes mutation, credential injection, external provider validation, production Telegram/Gateway connectivity, or publication.

## Secrets

Do not commit production secrets, host-local runtime state, credential stores, `.env` files, session state, gateway state, or generated rollback snapshots. Host-specific configuration must be created from templates and kept outside commits unless it contains only non-secret example values.

## Reporting

Until the repository is published, security findings should be tracked in the engineering review report and release checklist. After publication, replace this section with the project’s private disclosure channel.

## Required Security Checks

- Package checksum verification.
- Secret scan over source and release artifacts.
- Test coverage for live-target refusal and zero-mutation failure paths.
- Review of rollback and generated evidence boundaries before release.

