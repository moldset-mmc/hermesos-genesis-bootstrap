# 02_ARCHITECTURE_BASELINE.md
> Target Architecture Layers for Reproduced HermesOS
> Generated: 2026-07-11T23:30:00Z

## Target Architecture

```
+----------------------------------------------------------+
| A. VENDOR BASE (Hermes Agent v0.18.x)                     |
|    Authority: Upstream NousResearch                       |
|    Ownership: Open source (MIT)                           |
|    Mutability: Immutable during bootstrap (patched after) |
|    Portability: YES (pip install on any compatible OS)    |
|    Update: pip install --upgrade hermes-agent              |
+----------------------------------------------------------+
| B. AGENT PROFILE (hermesos profile)                       |
|    Authority: Hermes Agent profile mechanism              |
|    Ownership: Owner (Serghei)                             |
|    Mutability: Mutable via profile config                 |
|    Portability: YES (profile export/import)               |
|    Update: hermes profile operations                      |
+----------------------------------------------------------+
| C. IDENTITY / BEHAVIOR                                     |
|    Authority: HermesOS SOUL.md + HKP Constitution         |
|    Ownership: Owner                                        |
|    Mutability: Only by owner approval                     |
|    Portability: YES (profile files)                       |
|    Update: Via profile + SOUL.md changes                  |
+----------------------------------------------------------+
| D. GOVERNANCE (HKP Decision Gates + HKP Knowledge)        |
|    Authority: HKP Foundation                               |
|    Ownership: Owner                                        |
|    Mutability: Only via Foundation governance              |
|    Portability: YES (HKP_AUTHORITY_ROOT corpus)            |
|    Update: Via Foundation document updates                |
+----------------------------------------------------------+
| E. RUNTIME ENFORCEMENT (13 new + 15 patched files)        |
|    Authority: HKP Specification Layer                     |
|    Ownership: Shared Hermes Agent runtime                 |
|    Mutability: Patched via git during bootstrap           |
|    Portability: CONDITIONAL (requires compatible version) |
|    Update: Via git diff/patch mechanism                   |
+----------------------------------------------------------+
| F. VALIDATION (boot probe + test suite)                    |
|    Authority: HKP Validation Spec                         |
|    Ownership: Owner                                        |
|    Mutability: Append-only evidence                       |
|    Portability: YES (as scripts + expected results)        |
+----------------------------------------------------------+
| G. EVIDENCE (reports, SHA-256, logs)                      |
|    Authority: HKP Audit                                   |
|    Ownership: Owner                                        |
|    Mutability: Append-only                                 |
|    Portability: STATE-ONLY (generated per host)           |
+----------------------------------------------------------+
```

## Layer Classification Summary
| Layer | Authority | Portable | Immutable during bootstrap | Update mechanism |
|---|---|---|---|---|
| A. Vendor Base | Upstream | YES | YES | pip install |
| B. Profile | Owner | YES | NO (configured) | profile tools |
| C. Identity | Foundation | YES | NO (loaded) | SOUL.md update |
| D. Governance | Foundation | YES | NO (loaded) | doc update |
| E. Enforcement | HKP Spec | COND | NO (patched) | git diff |
| F. Validation | HKP Spec | YES | NO (run) | script update |
| G. Evidence | Owner | STATE | NO (generated) | per-run |

## Trust Boundary
Layer A is TRUSTED (authentic upstream)
Layers B-E are VERIFIED (via SHA-256 + owner approval)
Layer F is TESTED (via live validation)
Layer G is documented proof
