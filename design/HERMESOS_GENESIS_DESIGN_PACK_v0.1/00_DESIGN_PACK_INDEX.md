# 00_DESIGN_PACK_INDEX.md
> HermesOS Genesis Design Pack v0.1 — Index and Navigation
> Generated: 2026-07-11T23:30:00Z

## Purpose
Настоящий пакет определяет нормативный архитектурный контракт для создания
воспроизводимого HermesOS Genesis Bootstrap. Он связывает существующий
Hermes Foundation с текущей реализацией HermesOS и целевым bootstrap-продуктом.

## Authoritative Sources
1. Hermes Genesis / Foundation (E:\HKP\) — 8-level document hierarchy
2. HERMESOS_SOURCE_INVENTORY_v0.1 — factual source capture
3. HERMESOS_GENESIS_FOUNDATION_CROSSWALK_v0.1 — evidence-based gap analysis

## Reading Order
00 - INDEX (this document)
01 - PRODUCT DEFINITION (what we're building)
02 - ARCHITECTURE BASELINE (target architecture)
03 - BOOTSTRAP BOUNDARY MODEL (what bootstrap can/cannot do)
04 - HERMESOS IDENTITY SPEC (normative identity)
05 - HKP DECISION GATES SPEC (6 gates formalized)
06 - RUNTIME ENFORCEMENT SPEC (hard enforcement baseline)
07 - REGISTRY EXTENSION SPEC (new components proposal)
08 - BOOTSTRAP LIFECYCLE SPEC (14-phase lifecycle)
09 - PORTABILITY AND PATH MODEL (path parameterization)
10 - SECRETS AND TRUST MODEL (trust chain)
11 - VALIDATION AND READINESS SPEC (readiness levels)
12 - UPSTREAM COMPATIBILITY MODEL (Hermes version policy)
13 - ADR CANDIDATE REGISTER (8 proposed ADRs)
14 - OPEN GAPS AND DEFERRED SCOPE (v0.1 exclusions)
15 - RELEASE CRITERIA (gates for each stage)
manifest.yaml - machine-readable manifest

## Document Status
All documents in this pack: DESIGN DRAFT (version 0.1.0)
Authority classification marked per document

## Dependency Graph
00 -> 01 -> 02 -> 03 -> [04,05,06,07,08] -> [09,10,11,12] -> 13 -> 14 -> 15

## What This Pack Defines
- Target architecture for reproducible HermesOS
- Identity and behavior specification
- Decision gates specification
- Runtime enforcement baseline
- Bootstrap lifecycle (14 phases)
- Portability model
- Secrets and trust model
- Validation and readiness criteria
- ADR candidates
- Release criteria

## What This Pack Does NOT Define
- Production installer code
- Specific algorithm implementations
- Runtime patches (these are in Source Bundle + Implementation)
- Changes to existing Foundation documents
- Changes to canonical HKP
- GitHub repository structure
- Real secrets or credentials
- Operating Cycle implementation (deferred)
- Knowledge DNA implementation (deferred)
