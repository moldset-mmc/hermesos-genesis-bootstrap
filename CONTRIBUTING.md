# Contributing

Changes must preserve Design Pack and Foundation semantics. Implementation code is not architectural authority when it conflicts with normative design.

Before proposing release changes:

1. Verify the source bundle and release checksum manifests.
2. Run `python -m pytest tests -q`.
3. Keep generated runtime state, rollback snapshots, caches, and host secrets out of the repository.
4. Document any change to the Source Bundle, bootstrap implementation, or overlay disposition in release notes.

Architectural changes require owner review and an ADR or equivalent approval record.

