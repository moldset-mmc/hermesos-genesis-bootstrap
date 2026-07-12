# 05_HKP_DECISION_GATES_SPEC.md
> Normative Specification of 6 HKP Operational Decision Gates
> Generated: 2026-07-11T23:30:00Z

## Gate A — INTENT GATE

| Property | Value |
|---|---|
| Purpose | Prevent unintended system changes from ambiguous input |
| Trigger | User input with multiple materially different interpretations |
| Input | Natural language query |
| Decision states | LOOKUP, READ, EXPLAIN, SEARCH, CREATE, MODIFY, DELETE, RECORD |
| Allowed outputs | Determined action or clarification request |
| Failure behavior | If ambiguity unresolved -> BLOCK (no action) |
| Audit | Record ambiguous input and resolution |
| Foundation relation | NEW FORMALIZATION (partial alignment with Operating Model Phase 2) |
| Current enforcement | PROMPT-LEVEL only |
| Target enforcement | PROMPT-LEVEL (v0.1 — requires ADR for elevation) |
| ADR required | PROPOSED (ADR-01) |

## Gate B — EVIDENCE GATE

| Property | Value |
|---|---|
| Purpose | Ensure external facts are properly source-classified |
| Trigger | Any external fact used in reasoning or response |
| Decision states | PRIMARY_VERIFIED, SECONDARY_VERIFIED, OPENED_SOURCE, SEARCH_SNIPPET_ONLY, INFERENCE, UNKNOWN |
| Allowed outputs | Fact with properly marked source and confidence |
| Failure behavior | If insufficient evidence -> mark as UNKNOWN |
| Audit | Source classification recorded with fact |
| Foundation relation | NEW FORMALIZATION (Knowledge Model requires provenance but not this classification) |
| Current enforcement | PROMPT-LEVEL only |
| Target enforcement | PROMPT-LEVEL (v0.1) |
| ADR required | PROPOSED (ADR-01) |

## Gate C — CLAIM GATE

| Property | Value |
|---|---|
| Purpose | Verify every substantial claim before output |
| Trigger | Before every substantial factual answer |
| Decision states | Full check: source known, source open, evidence sufficient, fact or inference, confidence |
| Failure behavior | If insufficient -> communicate uncertainty explicitly |
| Audit | Claim confidence recorded in response |
| Foundation relation | NEW FORMALIZATION |
| Current enforcement | PROMPT-LEVEL only |
| Target enforcement | PROMPT-LEVEL (v0.1) |
| ADR required | PROPOSED (ADR-01) |

## Gate D — MEMORY ADMISSION GATE

| Property | Value |
|---|---|
| Purpose | Classify memory writes; prevent unverified/transient data in permanent memory |
| Trigger | Before memory tool write (add/replace/remove) |
| Decision states | PERMANENT_FACT, APPROVED_DECISION, USER_PREFERENCE, ACTIVE_PROJECT_STATE, VERIFIED_INTEGRATION, REFERENCE_ONLY, TEMPORARY, UNVERIFIED |
| Allowed in permanent | PERMANENT_FACT+evidence, APPROVED_DECISION, USER_PREFERENCE, confirmed ACTIVE_PROJECT_STATE, VERIFIED_INTEGRATION |
| Failure behavior | Deny unapproved classifications |
| Foundation relation | PARTIAL — aligns with Memory Governance (Operating Model Sec.8) |
| Current enforcement | PROMPT-LEVEL + RUNTIME-ASSISTED (context-level blocking) |
| Target enforcement | PROMPT-LEVEL + RUNTIME-ASSISTED (v0.1) |
| ADR required | PROPOSED if elevation to hard enforcement desired |

## Gate E — MUTATION GATE

| Property | Value |
|---|---|
| Purpose | Prevent unauthorized file/configuration mutations |
| Trigger | Before create/write/patch operations |
| Decision states | ALLOW, PROPOSE (owner approval required), BLOCK |
| Failure behavior | If owner did not request -> BLOCK |
| Foundation relation | PARTIAL — aligns with Constitution Art.6 (human decides) |
| Current enforcement | PROMPT-LEVEL + RUNTIME-ASSISTED (preflight blocks in non-foreground) |
| Target enforcement | RUNTIME-ASSISTED with Ed25519 approval integration (v0.1) |
| ADR required | NO (existing runtime support adequate) |

## Gate F — CORRECTION GATE

| Property | Value |
|---|---|
| Purpose | Recover from fabrication/error in memory |
| Trigger | Fabrication or error detected |
| Actions | Remove from memory, check contamination, restore to last confirmed state, record correction |
| Failure behavior | If contamination undetected -> risk of cascading errors |
| Foundation relation | NEW FORMALIZATION (partial alignment with Operating Model Sec.11 Failure Handling) |
| Current enforcement | PROMPT-LEVEL only |
| Target enforcement | PROMPT-LEVEL (v0.1) |
| ADR required | PROPOSED (ADR-01) |

## Summary
| Gate | Current | Target v0.1 | ADR |
|---|---|---|---|
| A. Intent | PROMPT | PROMPT | PROPOSED |
| B. Evidence | PROMPT | PROMPT | PROPOSED |
| C. Claim | PROMPT | PROMPT | PROPOSED |
| D. Memory | PROMPT+RUNTIME | PROMPT+RUNTIME | OPTIONAL |
| E. Mutation | PROMPT+RUNTIME | RUNTIME-ASSISTED+Ed25519 | NO |
| F. Correction | PROMPT | PROMPT | PROPOSED |
