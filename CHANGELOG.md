# Changelog

## Unreleased

- Normalized RC v0.1 into a GitHub repository candidate.
- Excluded generated rollback snapshots and runtime state from source repository layout.
- Added minimal repository hygiene, CI scaffold, and security/contribution guidance.
- Hardened bootstrap apply ordering so prepared-profile and profile-collision checks happen before disposable runtime mutation.
- Integrated the corrected `governance_status.py` into the v0.2 Source Bundle baseline; the historical RC v0.1 overlay remains provenance-only.
- Added deterministic release packaging, sealing, verification, and clean-install reconstruction automation.
- Adopted the MIT License and recorded Hermes Agent / Nous Research upstream attribution.
