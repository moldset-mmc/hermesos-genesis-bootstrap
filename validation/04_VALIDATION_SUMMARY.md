# Validation Summary

## Proven

| Check | Result | Evidence |
|---|---|---|
| Source Bundle SHA-256 integrity | PASS | Source Bundle metadata and implementation validation evidence |
| Clean official upstream baseline | PASS | commit `cd124ad1fae574dcdab8124924f84201d65277da` |
| Package compatibility | PASS | Hermes Agent `0.18.0` |
| Atomic preflight | PASS | clean-install unique preflight record |
| Patch applicability/application | PASS | clean-install lifecycle evidence |
| Profile and identity provisioning | PASS | clean-install lifecycle evidence |
| HKP authority binding | PASS | HKP-INT-006 authority checks |
| Runtime enforcement installation | PASS | staged runtime/import checks |
| Boot probe | PASS | `HKP GOVERNED / VERIFIED` |
| Rollback | PASS | profile/probe removed and runtime clean |
| Reproducibility from clean official Hermes | YES | `CLEAN_INSTALL_VALIDATION.json` |

## Not validated in clean-install mode

- External LLM provider inference;
- Telegram/Gateway production connectivity;
- Live permission matrix;
- Live subagent isolation.

These are explicitly limitations, not PASS claims.

## Evidence included

See `evidence/` and implementation package `evidence/`. Runtime-generated workspaces, caches and secret-bearing state are excluded from this RC.