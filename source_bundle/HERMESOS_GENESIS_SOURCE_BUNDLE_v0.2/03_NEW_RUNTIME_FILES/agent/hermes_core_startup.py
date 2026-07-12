#!/usr/bin/env python3
"""Hermes Core startup — sets process identity to hermes_core.

Place this in the Hermes Core startup chain so all core processes
have HERMES_PROCESS_IDENTITY=hermes_core.
"""
import os

# Set identity before any other imports
os.environ["HERMES_PROCESS_IDENTITY"] = "hermes_core"


def patch_auth_py():
    """Monkey-patch auth.py's credential read/write to go through broker.
    
    Called once at Hermes Core startup to ensure ALL credential paths
    route through the HKP-gated credential broker.
    """
    import hermes_cli.auth as auth_mod
    
    # Store originals
    _orig_read = auth_mod.read_credential_pool
    _orig_write = auth_mod.write_credential_pool
    _orig_load = auth_mod._load_auth_store
    _orig_save = auth_mod._save_auth_store
    
    def _brokered_read(provider_id=None):
        from agent.credential_broker import get_credentials
        result = get_credentials(provider_id)
        if "error" in result and "BLOCKED_BY" in str(result.get("error", "")):
            return {}  # Return empty on block
        return result
    
    def _brokered_write(provider_id, entries, removed_ids=None):
        from agent.credential_broker import write_credentials
        payload = {"entries": entries}
        if removed_ids:
            payload["removed_ids"] = removed_ids
        result = write_credentials(provider_id, payload)
        return result.get("success", True)  # Default True for legacy compat
    
    def _brokered_load_store(auth_file=None):
        from agent.hkp_enforcer import hkp_check
        decision = hkp_check(action="credential.read", target="auth_store")
        if not decision["allowed"]:
            raise PermissionError(f"BLOCKED_BY_HKP: {decision['reason']}")
        return _orig_load(auth_file)
    
    def _brokered_save_store(auth_store, target_path=None):
        from agent.hkp_enforcer import hkp_check
        decision = hkp_check(action="credential.write", target="auth_store")
        if not decision["allowed"]:
            raise PermissionError(f"BLOCKED_BY_HKP: {decision['reason']}")
        return _orig_save(auth_store, target_path)
    
    auth_mod.read_credential_pool = _brokered_read
    auth_mod.write_credential_pool = _brokered_write
    auth_mod._load_auth_store = _brokered_load_store
    auth_mod._save_auth_store = _brokered_save_store


# Set identity markers for various process types
_IDENTITY = os.environ.get("HERMES_PROCESS_IDENTITY", "").strip().lower()

if _IDENTITY == "hermes_core":
    # Full credential access allowed (HKP-gated)
    pass
elif _IDENTITY == "gateway":
    # Gateway processes: NO direct credential access
    pass
elif _IDENTITY == "cron":
    # Cron processes: NO direct credential access
    pass
elif _IDENTITY == "tools":
    # Tool runner processes: NO direct credential access
    pass
else:
    # Unknown/unset identity: treated as untrusted
    pass
