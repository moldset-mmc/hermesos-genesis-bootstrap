# 07_REGISTRY_EXTENSION_SPEC.md
> Proposal for Registry Extension
> Generated: 2026-07-11T23:30:00Z

This document does NOT modify HERMES_CORE_REGISTRY_v1.0.
It proposes components that have become architecturally significant since v1.0.

## Proposed New Components

### PC-01: Execution Context Subsystem
PURPOSE: Runtime context assignment and propagation for every tool/process
AUTHORITY: Security Model (Runtime Security)
LIFECYCLE: Active
REQUIRED: REQUIRED
CURRENT: agent/execution_context.py (7 contexts)
ADR: PROPOSED (ADR-02)

### PC-02: Tool Preflight Dispatcher
PURPOSE: Deny-by-default evaluation of every tool call against execution context
AUTHORITY: Security Model (Access Control)
LIFECYCLE: Active
REQUIRED: REQUIRED
CURRENT: agent/tool_preflight.py
ADR: PROPOSED (ADR-02)

### PC-03: HKP Runtime Enforcer
PURPOSE: Centralized check gate for cron, delivery, outbound operations
AUTHORITY: Security Model (Runtime Security)
LIFECYCLE: Active
REQUIRED: REQUIRED
CURRENT: agent/hkp_enforcer.py
ADR: PROPOSED (ADR-02)

### PC-04: Credential Broker
PURPOSE: Identity-based credential access control
AUTHORITY: Security Model (Identity Security)
LIFECYCLE: Active
REQUIRED: REQUIRED
CURRENT: agent/credential_broker.py + client + service
ADR: PROPOSED (ADR-02)

### PC-05: Approval Verification Service
PURPOSE: Ed25519-based approval token verification
AUTHORITY: Security Model (Explainable Security)
LIFECYCLE: Designed not operational
REQUIRED: OPTIONAL for v0.1
CURRENT: agent/approval_service.py
ADR: PROPOSED (ADR-02)

### PC-06: Validation / Evidence Subsystem
PURPOSE: Test suite, evidence collection, verification database
AUTHORITY: HKP Specification
LIFECYCLE: Proposed
REQUIRED: REQUIRED for release
CURRENT: verification_evidence.db (partial)
ADR: PROPOSED (ADR-02)

### PC-07: Genesis Bootstrap Package
PURPOSE: Self-contained deployable package for HermesOS creation
AUTHORITY: HKP Specification
LIFECYCLE: Design phase
REQUIRED: REQUIRED
CURRENT: Not yet created (this design pack)
ADR: DEFERRED
