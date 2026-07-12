# Governance Status Overlay Integration

RC v0.1 is immutable. Its source-bundle copy of
`gateway/governance_status.py` remains a historical record and its
`KEEP_AS_IMPLEMENTATION_OVERLAY` disposition is preserved in the v0.1 bundle.

The normalized repository's v0.2 source bundle carries the corrected
HKP-INT-006 / schema 1.0 implementation directly. The approval-safe engine
copies that component from the source bundle during APPLY and no longer reads,
validates, or copies a separate overlay. This disposition is recorded in the
v0.2 source manifest, provenance, changelog, and generated release notes.
