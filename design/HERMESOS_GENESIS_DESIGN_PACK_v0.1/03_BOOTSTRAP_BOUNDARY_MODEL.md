# 03_BOOTSTRAP_BOUNDARY_MODEL.md
> Bootstrap Boundaries: What bootstrap can and cannot do
> Generated: 2026-07-11T23:30:00Z

## Critical Distinctions

### BOOTSTRAP
Definition: Sequence of operations that transitions a system from non-existent
to operational according to pre-defined architecture.
EXAMPLES: Creating profile, loading identity, starting gateway.

### ADAPTATION
Definition: Modification of implementation to match approved specification
on a compatible but non-identical base version.
EXAMPLES: Applying git patches for HKP runtime enforcement on Hermes Agent v0.18.x.

### MIGRATION
Definition: Transferring state from one environment to another.
EXAMPLES: Restoring Honcho memory, copying HKP corpus.

### RUNTIME HARDENING
Definition: Application of security and governance controls to a runtime.
EXAMPLES: Deny-by-default preflight activation, credential broker enforcement.

### PROFILE PROVISIONING
Definition: Setting up agent profile with config, identity, and registries.
EXAMPLES: hermes profile create, copying SOUL.md.

## Actor Authority Boundaries

### Initial (stock) Hermes CAN:
- Receive a genesis package (download from trusted URL)
- Verify package integrity (SHA-256)
- Create a new profile (hermes profile create)
- Copy profile files from the package
- Start the new profile's gateway
- NOT: modify its own runtime without owner approval

### HermesOS (once started) CAN:
- Inspect the shared Hermes Agent runtime
- Compare against the approved baseline specification
- Apply approved runtime patches (from the genesis package)
- Validate the result
- NOT: modify HKP canonical artifacts
- NOT: change Foundation documents
- NOT: declare VERIFIED without evidence
- NOT: alter its own identity without owner approval

### Owner-Approved Actions:
- All runtime enforcement patching (requires owner consent)
- Profile creation on new environments
- Identity changes
- ADR-related architecture changes

### Architecture Changes vs Implementation Changes
IMPLEMENTATION CHANGE: Modifying tool_executor.py to add preflight gate
  -> This is ADAPTATION of existing architecture
ARCHITECTURE CHANGE: Creating a new governance layer not in Foundation
  -> This requires ADR

## Principle
HermesOS may ADAPT the implementation of an approved baseline to a compatible
version of Hermes Agent. It may NOT independently redefine the HKP authority
model or Foundation.

## Where Owner Approval is Required
1. Any action that creates, modifies, or deletes files outside profile scope
2. Any runtime enforcement change that affects other profiles
3. Any action requiring PROPOSE gate result
4. Gateway restart
5. Cron job creation/modification

## Where ADR is Required
8 candidates identified in 13_ADR_CANDIDATE_REGISTER.md
