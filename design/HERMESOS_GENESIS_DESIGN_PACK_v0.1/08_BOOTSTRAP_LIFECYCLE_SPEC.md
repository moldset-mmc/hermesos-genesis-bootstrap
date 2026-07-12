# 08_BOOTSTRAP_LIFECYCLE_SPEC.md
> 14-Phase Bootstrap Lifecycle
> Generated: 2026-07-11T23:30:00Z

## Phase 0 — DISCOVER ENVIRONMENT
ACTOR: Initial stock Hermes
PRECONDITION: Hermes Agent v0.18.x installed, pip verified
INPUTS: None
ACTIONS: Detect OS, detect Python version, detect hermes version, detect git availability
APPROVAL: None (diagnostic only)
SUCCESS: Environment report produced
FAILURE: If Hermes not installed -> BLOCK
EVIDENCE: environment_report.json

## Phase 1 — VERIFY OFFICIAL HERMES
ACTOR: Initial stock Hermes
INPUTS: Upstream version baseline (from package)
ACTIONS: Compare installed version against supported baseline
APPROVAL: None
SUCCESS: Version matches supported range
FAILURE: Version mismatch -> BLOCK with message
EVIDENCE: version_comparison.txt

## Phase 2 — RECEIVE TRUSTED GENESIS PACKAGE
ACTOR: Initial stock Hermes or human
INPUTS: Trusted GitHub URL or local path
ACTIONS: Download git archive or copy from local source
APPROVAL: Human provides URL or path
SUCCESS: Package directory present
FAILURE: Download fails -> BLOCK
EVIDENCE: package_receipt_log.txt

## Phase 3 — VERIFY PACKAGE INTEGRITY
ACTOR: Initial stock Hermes
INPUTS: Package directory, SHASUMS file
ACTIONS: SHA-256 verify all files against manifest
APPROVAL: None (automated)
SUCCESS: All checksums match
FAILURE: Mismatch -> BLOCK with details
EVIDENCE: integrity_verification_report.txt

## Phase 4 — CREATE HERMESOS PROFILE
ACTOR: Initial stock Hermes
INPUTS: Profile files from package (SOUL.md, config.yaml template, etc.)
ACTIONS: hermes profile create hermesos -> copy files
APPROVAL: None (standard Hermes operation)
SUCCESS: Profile exists with correct files
FAILURE: Profile creation fails -> BLOCK
EVIDENCE: profile_creation_log.txt

## Phase 5 — LOAD IDENTITY
ACTOR: Initial stock Hermes or human
INPUTS: SOUL.md, MEMORY.md, USER.md, registries
ACTIONS: Ensure identity files in profile, verify content
APPROVAL: Human confirms identity
SUCCESS: All identity files present and correct
FAILURE: Missing identity files -> BLOCK
EVIDENCE: identity_verification.txt

## Phase 6 — LOAD HKP GOVERNANCE
ACTOR: Initial stock Hermes or human
INPUTS: HKP knowledge corpus (33 canonical documents)
ACTIONS: Copy HKP corpus to HKP_AUTHORITY_ROOT
APPROVAL: None (governance loading)
SUCCESS: HKP corpus at target path
FAILURE: Missing documents -> BLOCK
EVIDENCE: governance_load_log.txt

## Phase 7 — START HERMESOS
ACTOR: Human
INPUTS: hermesos profile, .env with secrets
ACTIONS: Start gateway with --profile hermesos
APPROVAL: Human starts gateway
SUCCESS: Gateway running, HKP_AUTHORITY_ROOT set
FAILURE: Gateway fails to start -> BLOCK
EVIDENCE: gateway_state.json shows running

## Phase 8 — INSPECT SHARED RUNTIME
ACTOR: New HermesOS
INPUTS: None
ACTIONS: Detect hermes-agent version, check git status, compare against approved baseline
APPROVAL: None (read-only diagnostic)
SUCCESS: Gap analysis produced
FAILURE: HermesOS cannot inspect runtime -> BLOCK
EVIDENCE: runtime_inspection_report.txt

## Phase 9 — PLAN APPROVED ADAPTATION
ACTOR: New HermesOS
INPUTS: Gap analysis, approved baseline spec
ACTIONS: Generate adaptation plan (which patches to apply)
APPROVAL: HUMAN MUST APPROVE plan before execution
SUCCESS: Plan produced and approved
FAILURE: No approval -> BLOCK
EVIDENCE: approved_adaptation_plan.txt

## Phase 10 — APPLY RUNTIME ENFORCEMENT
ACTOR: New HermesOS
INPUTS: Approved plan, patches from package
ACTIONS: Apply git patches (13 new + 15 modified files), rebuild
APPROVAL: From Phase 9
SUCCESS: All patches apply cleanly, no conflicts
FAILURE: Patch conflict -> BLOCK with details; rollback available
EVIDENCE: patch_application_log.txt

## Phase 11 — RESTART / RELOAD
ACTOR: New HermesOS or human
INPUTS: Rebuilt runtime
ACTIONS: Stop gateway, start gateway with enforcement active
APPROVAL: Human or automated restart
SUCCESS: Gateway restarts successfully
FAILURE: Gateway fails after restart -> ROLLBACK
EVIDENCE: restart_log.txt

## Phase 12 — VALIDATE
ACTOR: New HermesOS
INPUTS: Validation suite from package
ACTIONS: Run all validation tests (identity, governance, enforcement, isolation)
APPROVAL: None (automated)
SUCCESS: ALL tests pass
FAILURE: Any test fails -> BLOCK
EVIDENCE: validation_report.txt

## Phase 13 — PRODUCE EVIDENCE
ACTOR: New HermesOS
INPUTS: All phase logs and reports
ACTIONS: Collect all evidence into evidence package
APPROVAL: None
SUCCESS: Evidence package complete
EVIDENCE: evidence_package.zip + sha256

## Phase 14 — DECLARE READY
ACTOR: New HermesOS
INPUTS: Valid evidence package
ACTIONS: Produce final READY report, notify owner
APPROVAL: Owner acknowledges readiness
SUCCESS: HermesOS declared READY
FAILURE: Any previous phase failed -> NOT READY
EVIDENCE: ready_declaration.txt