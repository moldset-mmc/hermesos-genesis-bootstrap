# 11_VALIDATION_AND_READINESS_SPEC.md
> Validation and Readiness Specification
> Generated: 2026-07-11T23:30:00Z

## Readiness Levels
| Level | Definition | Validation |
|---|---|---|
| SOURCE PRESENT | Package delivered and verified | SHA-256 match |
| CONFIGURED | Profile created, identity loaded | File existence check |
| STARTED | Gateway running | gateway_state.json shows running |
| SOURCE VERIFIED | Patches applied, runtime rebuilt | git status matches expected |
| LIVE VERIFIED | Tool permissions work as specified | Live test execution |
| ISOLATION VERIFIED | Security boundaries work | Isolation test execution |
| READY | All tests pass, evidence produced | Complete evidence package |

## Mandatory Validation Tests for v0.1

### Identity Validation
1. SOUL.md present with required fields
2. config.yaml has model routing configured
3. MEMORY.md and USER.md present
4. PROJECT_REGISTRY.yaml and CONNECTOR_REGISTRY.yaml present

### Governance Prompt Validation
1. HKP_AUTHORITY_ROOT set and accessible
2. hkp_boot_probe.py runs and produces VERIFIED result
3. System prompt includes HKP governance block

### Runtime Enforcement Validation
1. UNKNOWN context: all non-diagnostic tools -> BLOCKED (SOURCE VERIFIED)
2. FOREGROUND_OWNER: write tools work
3. SUBAGENT: all write tools -> BLOCKED
4. Memory governance target -> DENY
5. Sensitive path write in CRON -> BLOCKED

### Permissions Matrix Validation
Full matrix from 06_CAPABILITY_AND_PERMISSION_BASELINE.yaml tested per context.

### Isolation Validation
1. Subagent cannot delegate_task
2. Subagent cannot write_file
3. Subagent cannot terminal
4. UNKNOWN cannot write to files
5. CRON agent cannot cronjob

### Restart Persistence Validation
1. Gateway restart preserves HKP enforcement
2. Boot probe runs on restart

### Rollback Validation
1. git checkout -- . restores original runtime
2. Removing untracked files restores original state

### Secret Absence Validation
Package directory and profile files scanned for real API key patterns

## Minimum PASS Baseline for v0.1
- ALL identity tests: PASS
- ALL governance prompt tests: PASS
- Enforcement tests: 3 of 5 live, rest SOURCE VERIFIED
- Isolation: SUBAGENT and UNKNOWN PASS
- Restart persistence: PASS
- Rollback: VERIFIED
- Secret scan: PASS

## Failure Policy
Any FAIL in identity, governance, or isolation -> BLOCK.
Enforcement tests that are source-only are acceptable for v0.1
but must be live-verified before v1.0.