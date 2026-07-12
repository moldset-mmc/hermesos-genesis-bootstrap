# Compatibility Baseline

| Property | Supported value |
|---|---|
| Upstream repository | `https://github.com/NousResearch/hermes-agent.git` |
| Upstream package | `hermes-agent==0.18.0` |
| Pinned commit | `cd124ad1fae574dcdab8124924f84201d65277da` |
| Python | `>=3.11` |
| Patch application | `git apply -p0 --check` then `git apply -p0` |
| HKP integrity anchor | `HKP_INTEGRITY_MANIFEST_v6.0.json` / `HKP-INT-006` |

The package is version-locked. Any upstream change requires a new inventory, crosswalk, patch, bundle and clean-install validation.

The boot probe deploys to:

```text
<HERMES_HOME>/scripts/hkp_boot_probe.py
```

The minimum corpus is a bootstrap dependency corpus only. It is not a substitute for the owner-bound authoritative HKP root.

The current implementation overlay corrects `gateway/governance_status.py` to the RC2.6 / HKP-INT-006 authority chain. Source Bundle originals remain unmodified.
