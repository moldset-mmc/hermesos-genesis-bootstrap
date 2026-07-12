# 12_UPSTREAM_COMPATIBILITY_MODEL.md
> Upstream Compatibility Model
> Generated: 2026-07-11T23:30:00Z

## Supported Baseline (v0.1)
| Property | Value |
|---|---|
| Repository | github.com/NousResearch/hermes-agent.git |
| Branch | main |
| Pinned commit | cd124ad1f |
| pip version | hermes-agent == 0.18.0 |
| Python | >= 3.11 |

## Compatibility Detection
Before any action, HermesOS must:
1. Detect installed version: `pip show hermes-agent`
2. Detect git state: `git log -1 --format=%H` in installed directory
3. Compare against supported baseline
4. Produce version_comparison.txt

## Version Mismatch Behavior
- MINOR version mismatch (0.18.x where x differs): WARNING but proceed if patches apply
- MAJOR version mismatch (0.19+ or 0.17-): BLOCK
- Unknown commit on same minor: WARNING, diff analysis, PROPOSE to owner

## Patch Application Strategy
1. Patches generated as git format-patch from known working commit
2. Applied in deterministic order
3. If patch conflicts: STOP, produce conflict report, DO NOT force-apply
4. Owner must resolve conflicts manually

## Source Adaptation Policy
Genesis package is version-locked to a specific Hermes Agent baseline.
Adaptation to other versions requires a new package version.

## Refusal Conditions
Bootstrap MUST refuse if:
1. Hermes Agent version not in supported range
2. Python < 3.11
3. Git not available
4. Package integrity verification fails
5. Owner approval not obtained for Phase 9
6. Required secrets not injected

## Future Version Migration Policy
When upstream releases a new version:
1. Create new source inventory against new version
2. Create new crosswalk analysis
3. Update patches
4. Create new source bundle
5. Validate against clean install
6. Release new genesis package version
