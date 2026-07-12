# Known Limitations

1. External provider inference was not validated in the clean-install test.
2. Telegram/Gateway production connectivity was not validated.
3. Live permissions and isolation matrix require real runtime execution.
4. The current local Hermes reference implementation has separate convergence findings and is not a clean-bootstrap target.
5. `governance_status.py` correction remains an implementation overlay:

```text
STALE_IMPLEMENTATION
KEEP_AS_IMPLEMENTATION_OVERLAY
```

6. This RC has not been published to GitHub.
7. This RC does not establish `LIVE VERIFIED`, `ISOLATION VERIFIED`, or `READY`.

None of these limitations invalidates the proven clean-install local lifecycle, boot probe, or rollback result.