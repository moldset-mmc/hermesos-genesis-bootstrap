# 15_RELEASE_CRITERIA.md
> Release Criteria and Stage Gates
> Generated: 2026-07-11T23:30:00Z

## Stage Gates

### Gate 1: DESIGN PACK -> SOURCE BUNDLE
Criteria:
- All design specification documents complete
- ADR candidates documented
- Gaps documented
- Portability model defined
- Secrets model defined
- Validation spec defined
PASS: Design pack approved by owner

### Gate 2: SOURCE BUNDLE -> IMPLEMENTATION
Criteria:
- All source materials extracted (git patches, profile files, HKP corpus subset)
- Host-specific paths parameterized
- Secrets stripped from all files
- SHA-256 manifest of all bundle files
- Template .env created
PASS: Bundle integrity verified

### Gate 3: IMPLEMENTATION -> RELEASE CANDIDATE
Criteria:
- Bootstrap scripts written and tested on development host
- All 14 phases implemented
- Validation suite implemented
- Rollback mechanism implemented
- Secrets injection mechanism implemented
PASS: Bootstrap run produces READY state on dev host

### Gate 4: RELEASE CANDIDATE -> CLEAN INSTALL TEST
Criteria:
- Hermes Agent installed on clean VM/container from pip
- No existing HermesOS profile or HKP corpus
- RC package deployed and executed
- All 14 phases completed
- READY state achieved
PASS: Full clean install test passes

### Gate 5: CLEAN INSTALL TEST -> GITHUB RELEASE
Criteria:
- NO secrets in package
- NO host-specific paths in package
- Pinned upstream baseline documented
- Reproducible package (same input -> same result)
- Validation suite complete and passing
- Clean Hermes test evidence produced
- Rollback path documented
- Release manifest generated
- Checksums published
- Release tag created
PASS: GitHub release published

## GitHub Release Mandatory Checks
1. secret scanning: PASS (no patterns found)
2. host-path scanning: PASS (no hardcoded C:\ or /home/ paths)
3. integrity: SHA-256 manifest matches all files
4. version: Package version matches release tag
5. dependency: Upstream baseline commit hash pinned
6. validation: Test evidence bundle included
7. rollback: Rollback procedure documented
8. license: MIT (or chosen license)
9. README: Installation and usage instructions
