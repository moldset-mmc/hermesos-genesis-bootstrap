# HermesOS Genesis Bootstrap Implementation v0.1

## Purpose
Deterministic, resumable implementation of Design Pack DP-08. It is an implementation package, not authority to mutate a live Hermes runtime.

## Safety boundary
- `LIVE_TARGET: true` is refused by `APPLY`.
- `APPLY` requires `--disposable-target` and first executes `git apply -p0 --check`.
- The original Source Bundle patch omits `a/` and `b/` prefixes; its deterministic application form is `git apply -p0`.
- Boot probe is a `HERMES_HOME_RUNTIME_SUPPORT` artifact installed at `<HERMES_HOME>/scripts/hkp_boot_probe.py`, as required by the gateway template; it is not a shared runtime-root file.
- `BOOTSTRAP_MINIMUM_CORPUS` is a dependency corpus only. It is never promoted to the owner-bound authoritative HKP root.
- The owner-bound current integrity anchor is `HKP_INTEGRITY_MANIFEST_v6.0.json` / `HKP-INT-006` / RC2.6. The historical v1.3 / HKP-INT-004 status-reader expectation is corrected only through `runtime_corrections/`; the Source Bundle is unchanged.
- Secret bindings are references only. Values are neither read nor written to evidence.

## Modes
| Mode | Function | Mutation |
|---|---|---|
| `INSPECT` | Host/runtime discovery | No |
| `VALIDATE_PACKAGE` | SHA-256 package verification | No |
| `PLAN` | Inspectable mutation plan | Plan artifact only |
| `PREPARE` | Prepare profile payload in workspace | Disposable workspace only |
| `APPLY` | Patch a disposable runtime | Disposable only; live blocked |
| `VALIDATE` | Static/disposable validation status | No live start |
| `ROLLBACK` | Disposable git rollback | Live blocked |
| `STATUS` | Read resumable state | No |

## Execution

`bootstrap_engine/genesis_bootstrap_v2.py` is the **sole approval-safe executable engine**. `genesis_bootstrap.py` is `LEGACY_NOT_FOR_EXECUTION` and only forwards to v2 for compatibility.

Use a host-specific bindings file created from `config_templates/host-bindings.template.json`.

```bash
python bootstrap_engine/genesis_bootstrap_v2.py INSPECT --config bindings.json
python bootstrap_engine/genesis_bootstrap_v2.py VALIDATE_PACKAGE --config bindings.json
python bootstrap_engine/genesis_bootstrap_v2.py PREFLIGHT --config bindings.json
python bootstrap_engine/genesis_bootstrap_v2.py PLAN --config bindings.json
python bootstrap_engine/genesis_bootstrap_v2.py PREPARE --config bindings.json --disposable-target
python bootstrap_engine/genesis_bootstrap_v2.py APPLY --config bindings.json --disposable-target
```

For a live target, `LIVE_TARGET_INSPECTION` and `PLAN_LIVE` are read-only. `PLAN_LIVE` requires `LIVE_TARGET=true` and a current `COMPATIBLE` inspection; it is blocked for a dirty or incompatible target.

## Live-apply gate
A live target can only be considered after reconstruction and disposable validation evidence is reviewed. This package will stop at **OWNER APPROVAL REQUIRED FOR LIVE APPLY**. No runtime change, gateway restart, profile creation in the live Hermes home, or secret injection is performed by this implementation stage.

## Evidence
Each engine action writes a JSON record with timestamp, target, inputs, action, result, verification level and failure detail. Human-readable phase reports are stored under `evidence/` where applicable.
