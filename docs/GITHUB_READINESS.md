# GitHub Readiness Notes

This repository candidate is ready for source-control import after the final
engineering validation recorded in the review report.

Required before publication:

- Keep RC v0.1 immutable and retain its overlay disposition as historical provenance.
- Generate release artifacts only through `scripts/release.py`; it rejects secrets, generated state, and integrity failures.
- CI runs syntax/tests, source/release integrity verification, secret scanning, forbidden-state scanning, and deterministic packaging.
- Example evidence is intentionally non-secret and remains in the repository as review material.
