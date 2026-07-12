# 06_RUNTIME_ENFORCEMENT_SPEC.md
> Hard Enforcement Baseline Specification
> Generated: 2026-07-11T23:30:00Z

## Enforcement Rules (Normative)

### ER-01: ExecutionContext UNKNOWN
REQUIREMENT: When no context is established, deny-by-default.
Only diagnostic tools (read_file, search_files, READ_ONLY tools) allowed.
RATIONALE: Fail-closed safety.
AFFECTED: All tools
EXPECTED: BLOCKED for writes, outbound, delegation, cron, exec
SOURCE: Security Model (Least Privilege, Zero Trust)
VALIDATION: UNKNOWN context -> verify all non-diagnostic tools return BLOCKED

### ER-02: FOREGROUND_OWNER context
REQUIREMENT: Authenticated owner gets maximum permissions.
All tools ALLOWED (with PROPOSE for delete, cronjob; DENY for governance memory).
RATIONALE: Owner authority per Constitution Art.6.
AFFECTED: All tools
EXPECTED: Full access with governance restrictions
SOURCE: Constitution Art.6
VALIDATION: Authorized Telegram session -> verify write_file works, governance memory blocked

### ER-03: SUBAGENT isolation
REQUIREMENT: Subagent spawned via delegate_task gets SUBAGENT context.
All write tools BLOCKED. Only read_file, search_files, memory (non-sensitive) ALLOWED.
RATIONALE: Delegation execution does not equal delegation of authority.
AFFECTED: delegate_task -> child agent
EXPECTED: Write_file, patch, terminal, memory write -> BLOCKED
SOURCE: Operating Model Sec.6 (Delegation Model)
VALIDATION: Subagent -> verify write tools return BLOCKED

### ER-04: CRON enforcement
REQUIREMENT: Cron jobs pass HKP hkp_check() gate.
Emergency stop (HKP_EMERGENCY_STOP) kills ALL cron dispatching.
RATIONALE: Cron runs without user supervision.
AFFECTED: cron/scheduler.py
EXPECTED: All jobs pass hkp_check; emergency stop = 0 jobs dispatched
SOURCE: Security Model (Runtime Security)
VALIDATION: Create test job -> verify gate fires; set emergency stop -> verify tick returns 0

### ER-05: Delivery enforcement
REQUIREMENT: Every outbound platform message passes hkp_check().
RATIONALE: Prevent unauthorized outbound communication.
AFFECTED: gateway/delivery.py, telegram/adapter.py
EXPECTED: All sends pass HKP gate
SOURCE: Security Model (Runtime Security)
VALIDATION: Trigger blocked delivery -> verify error returned

### ER-06: Memory write restrictions
REQUIREMENT: Memory writes blocked in UNKNOWN, SUBAGENT, BACKGROUND_REVIEW, CRON contexts.
Governance target memory -> DENY. Canonical target -> PROPOSE.
RATIONALE: Memory modification requires trust.
AFFECTED: memory_tool.py, tool_preflight.py
EXPECTED: Blocked in non-foreground contexts; governance=DENY; canonical=PROPOSE
SOURCE: Operating Model Sec.8 (Memory Governance)
VALIDATION: Subagent memory write -> BLOCKED; governance memory write -> DENY

### ER-07: Sensitive path protection
REQUIREMENT: Paths matching patterns (.env, config.yaml, credentials, secrets, /HKP/)
are PROPOSE in foreground, BLOCKED in all other contexts.
RATIONALE: Protect system configuration and secrets.
AFFECTED: file_tools.py (write_file), patch tool
EXPECTED: Sensitive path in FOREGROUND = PROPOSE; in CRON = BLOCKED
SOURCE: Security Model (Knowledge Security)
VALIDATION: Write to .env in CRON -> BLOCKED

### ER-08: Credential isolation
REQUIREMENT: Only HERMES_PROCESS_IDENTITY=hermes_core can read credentials.
All other identities -> DENY.
RATIONALE: Prevent credential exfiltration.
AFFECTED: credential_broker.py, credential_pool.py
EXPECTED: Gateway process -> credential access DENY
SOURCE: Security Model (Identity Security)
VALIDATION: Non-hermes_core process -> verify credential access blocked

### ER-09: Skill governance protection
REQUIREMENT: Governance class skills -> DENY. Canonical/approved -> PROPOSE.
Operational/draft -> ALLOWED in FOREGROUND.
RATIONALE: Governance skills define system behavior.
AFFECTED: skill_manager_tool.py
EXPECTED: Governance skill create -> DENY
SOURCE: Registry (Governance Components)
VALIDATION: Try create governance skill -> verify DENY

## Technology-Neutral Expression
The enforcement rules above are expressed without Python-specific references.
They define WHAT must be enforced, not HOW. The current implementation
(execution_context.py, tool_preflight.py) serves as a REFERENCE IMPLEMENTATION
but is not the only valid implementation.
