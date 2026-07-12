# 09_PORTABILITY_AND_PATH_MODEL.md
> Portability Model and Path Parameterization
> Generated: 2026-07-11T23:30:00Z

## Principles
1. NO hardcoded host paths in any normative specification
2. ALL paths parameterized via environment variables or config files
3. OS abstraction where applicable
4. Clear separation: portable config vs host binding vs secret binding vs generated state

## Parameterization Model

### Portable Configuration (INHERITED from Foundation)
| Parameter | Windows Default | Linux Default |
|---|---|---|
| HERMES_HOME | %LOCALAPPDATA%\hermes | ~/.local/share/hermes |
| HKP_AUTHORITY_ROOT | $HERMES_HOME\hkp | $HERMES_HOME/hkp |
| Profile root | $HERMES_HOME\profiles\<name>\ | $HERMES_HOME/profiles/<name>/ |

### Host Bindings (EXTENDED — must be set per deployment)
| Binding | Default | Override |
|---|---|---|
| EVIDENCE_BASE | $HKP_AUTHORITY_ROOT/Runtime Layer/audit | env var |
| POLICY_ROOT | $HKP_AUTHORITY_ROOT/Specification Layer/ | env var |
| APPROVAL_KEY_PATH | $HKP_AUTHORITY_ROOT/Specification/approved/ | env var |

### Secret Bindings (injected after install, NEVER in package)
- .env — API keys for LLM providers, Telegram tokens
- credentials/ — Connector-specific credential files

### Generated State (NOT portable, regenerated per host)
- state.db — Session history
- verification_evidence.db — Test results
- honcho.json — Honcho memory state
- cron/jobs.json — Cron job scheduling

## OS Abstraction Rules
Paths in specifications use forward-slash notation (/) as universal separator.
Platform-specific translation is done by the bootstrap implementation.
Example: $HERMES_HOME/profiles/hermesos/SOUL.md
  Windows: C:\Users\<user>\AppData\Local\hermes\profiles\hermesos\SOUL.md
  Linux: /home/<user>/.local/share/hermes/profiles/hermesos/SOUL.md

## Current Implementation Notes (NOT normative)
The current HermesOS uses host-specific paths that are NOT part of any norm:
- HERMES_HOME = C:\Users\molds\AppData\Local\hermes (HOST-SPECIFIC)
- HKP_AUTHORITY_ROOT = E:\HKP\ (HOST-SPECIFIC)
- EVIDENCE_BASE = E:/HKP/Runtime Layer/audit/policy_gate/reports (HOST-SPECIFIC)
These must be overridden per deployment via env vars.