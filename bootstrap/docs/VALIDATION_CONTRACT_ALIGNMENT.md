# Validation Contract Alignment

| Claimed gate | Engine check | Status |
|---|---|---|
| Package integrity | `VALIDATE_PACKAGE`: all Source Bundle SHA-256 records | Implemented |
| Exact baseline | `PREFLIGHT`: commit and `pyproject.toml` version | Implemented |
| Target cleanliness | `PREFLIGHT`: `git status --porcelain=v1` must be empty | Implemented |
| Exact mutation paths | parser retains non-prefixed diff paths; equality to manifest | Implemented |
| Custom sources / overlay / collision checks | `PREFLIGHT` | Implemented |
| Host bindings / secret references | `PREFLIGHT`, references only | Implemented |
| Snapshot readiness | `PREFLIGHT` and snapshot directory test | Implemented |
| Safe rollback | snapshot backup + deterministic restore, disposable-tested | Implemented |
| Boot probe / authority compatibility | Previous disposable validation evidence | Implemented in disposable validation |
| Gateway external start | Requires credentials/connectivity | Not executable in disposable mode |
| Live permissions matrix | Requires live execution contexts | Not implemented / not claimed |
| Live subagent isolation | Requires live execution contexts | Not implemented / not claimed |

`VALIDATE` reports only the checks implemented by the engine. It does not claim live validation, isolation verification, or readiness.
