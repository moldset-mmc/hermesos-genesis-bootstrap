# 13_ADR_CANDIDATE_REGISTER.md
> Architecture Decision Record Candidates from Crosswalk
> Generated: 2026-07-11T23:30:00Z

## ADR-01: Decision Gates Elevation
TITLE: Should 6 HKP Decision Gates be elevated from prompt-level to runtime-enforced?
ORIGIN: Crosswalk — 4 of 6 gates have ZERO runtime enforcement
PROPOSED: Defer to v0.2. Keep at prompt-level for v0.1
FOUNDATION: Foundation Decision Model describes general validation, not specific gate classifications
ALTERNATIVES: (a) Encode in preflight (b) Keep prompt-only (c) Hybrid
IMPACT: Low for v0.1
RISK: Model may not comply with gates
STATUS: PROPOSED

## ADR-02: Registry Extension
TITLE: Should official Registry be extended with Runtime Enforcement components?
ORIGIN: Crosswalk — 7 new components exist outside v1.0 Registry
PROPOSED: Create proposal doc, defer official update to v1.0
FOUNDATION: Registry v1.0 predates HKP runtime layer
IMPACT: Medium
STATUS: PROPOSED

## ADR-03: Bootstrap vs Runtime Patching
TITLE: Does runtime patching violate the Bootstrap principle?
ORIGIN: Crosswalk CONFLICT-02
PROPOSED: Runtime patching = architecture deployment, not architecture change
FOUNDATION: Original Bootstrap assumes static pre-deployed architecture
IMPACT: Medium
STATUS: PROPOSED

## ADR-04: Hermes Core vs Multi-Profile Architecture
TITLE: Is HermesOS a valid implementation of Hermes Core?
ORIGIN: Crosswalk DRIFT-03
PROPOSED: HermesOS is a valid IMPLEMENTATION of Core principles within multi-agent architecture
FOUNDATION: Foundation assumes single Core entity
IMPACT: High
STATUS: PROPOSED

## ADR-05: 9-Phase Operating Cycle Implementation
TITLE: Should Operating Cycle be explicitly implemented?
ORIGIN: Crosswalk GAP-01
PROPOSED: DEFERRED — not in v0.1 scope
STATUS: PROPOSED

## ADR-06: Knowledge DNA Implementation
TITLE: Should Knowledge DNA be runtime code structure?
ORIGIN: Crosswalk GAP-03
PROPOSED: DEFERRED
STATUS: PROPOSED

## ADR-07: Constitution Injection
TITLE: Should Constitution text be injected into HermesOS system prompt?
ORIGIN: Crosswalk GAP-06
PROPOSED: YES for v0.1
IMPACT: Low
STATUS: PROPOSED

## ADR-08: ADR Registry in Runtime
TITLE: Should ADRs be tracked in machine-readable runtime registry?
ORIGIN: Crosswalk GAP-08
PROPOSED: DEFERRED
STATUS: PROPOSED
