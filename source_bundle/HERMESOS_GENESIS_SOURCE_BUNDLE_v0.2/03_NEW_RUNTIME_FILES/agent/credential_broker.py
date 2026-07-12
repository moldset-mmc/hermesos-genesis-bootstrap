"""Credential broker — gates ALL credential access through HKP enforcement.

Architecture:
  Hermes Core (identity=hermes_core) → broker → auth.json
  Gateway (identity=gateway)        → broker → DENY (no direct access)
  Cron (identity=cron)              → broker → DENY (no direct access)
  Tools (identity=tools)            → broker → DENY (no direct access)
  Other (identity=unknown)          → broker → DENY (unknown identity)

The broker:
  - Reads auth.json ONLY for hermes_core identity
  - Returns restricted/limited creds for approved gateways
  - Goes through hkp_check() for every access
  - Audits every access
  - Fail-closed on broker/policy outage

Usage::

    from agent.credential_broker import CredentialBroker
    broker = CredentialBroker()
    creds = broker.get_credentials(provider_id="anthropic")
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Identity marker ───────────────────────────────────────────────────────
_HERMES_PROCESS_IDENTITY_VAR = "HERMES_PROCESS_IDENTITY"

# Valid identities
IDENTITY_HERMES_CORE = "hermes_core"
IDENTITY_GATEWAY = "gateway"
IDENTITY_CRON = "cron"
IDENTITY_TOOLS = "tools"
IDENTITY_WORKFLOW = "workflow"
IDENTITY_EMPLOYEE_PROFILE = "employee_profile"
IDENTITY_CHILD_PROCESS = "child_process"
IDENTITY_UNKNOWN = "unknown"

_VALID_IDENTITIES = frozenset({
    IDENTITY_HERMES_CORE,
    IDENTITY_GATEWAY,
    IDENTITY_CRON,
    IDENTITY_TOOLS,
    IDENTITY_WORKFLOW,
    IDENTITY_EMPLOYEE_PROFILE,
    IDENTITY_CHILD_PROCESS,
})

# Only hermes_core can directly access credentials
_CREDENTIAL_PRIVILEGED_IDENTITIES = frozenset({
    IDENTITY_HERMES_CORE,
})


def get_process_identity() -> str:
    """Return the current process identity from env var."""
    identity = os.environ.get(_HERMES_PROCESS_IDENTITY_VAR, "").strip().lower()
    if identity in _VALID_IDENTITIES:
        return identity
    return IDENTITY_UNKNOWN


def set_process_identity(identity: str) -> None:
    """Set the process identity for this process and all children."""
    if identity in _VALID_IDENTITIES:
        os.environ[_HERMES_PROCESS_IDENTITY_VAR] = identity


# ── Credential broker singleton ────────────────────────────────────────────
class _CredentialBroker:
    """Internal broker singleton — gates credential access through HKP."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}

    def _get_identity(self) -> str:
        return get_process_identity()

    def _hkp_gate(self, action: str, target: str) -> dict:
        """Call hkp_check or fail closed."""
        try:
            from agent.hkp_enforcer import hkp_check
            return hkp_check(action=action, target=target)
        except ImportError:
            # Fail closed: enforcer unavailable → deny
            return {"allowed": False, "reason": "HKP_ENFORCER_UNAVAILABLE", "policy_class": "FAIL_CLOSED"}
        except Exception as exc:
            return {"allowed": False, "reason": f"HKP_CHECK_FAILED: {exc}", "policy_class": "FAIL_CLOSED"}

    def _audit(self, action: str, target: str, result: str, reason: str = "") -> None:
        """Write audit record."""
        try:
            from agent.hkp_enforcer import hkp_audit
            hkp_audit(action=action, target=target, result=result, reason=reason)
        except Exception:
            pass  # Audit failure must not block the system

    def get_credentials(self, provider_id: Optional[str] = None) -> dict[str, Any]:
        """Get credentials from auth.json through HKP-gated broker.

        Only hermes_core identity can read credentials directly.
        All other identities get empty response.
        """
        identity = self._get_identity()

        # 1. HKP gate check
        gate_decision = self._hkp_gate(
            action="credential.read",
            target=provider_id or "all"
        )
        if not gate_decision["allowed"]:
            self._audit(
                action="credential.read",
                target=provider_id or "all",
                result="DENIED",
                reason=f"HKP gate blocked: {gate_decision['reason']}"
            )
            return {"error": f"BLOCKED_BY_HKP: {gate_decision['reason']}"}

        # 2. Identity check (second layer)
        if identity not in _CREDENTIAL_PRIVILEGED_IDENTITIES:
            self._audit(
                action="credential.read",
                target=provider_id or "all",
                result="DENIED",
                reason=f"identity '{identity}' not authorized for direct credential access"
            )
            return {"error": f"BLOCKED_BY_BROKER: identity '{identity}' not authorized"}

        # 3. Read the credentials
        try:
            # Import lazily to avoid circular imports
            import hermes_cli.auth as auth_mod

            if provider_id:
                creds = auth_mod.read_credential_pool(provider_id=provider_id)
            else:
                creds = auth_mod.read_credential_pool()

            self._audit(
                action="credential.read",
                target=provider_id or "all",
                result="ALLOWED",
                reason=f"identity={identity}"
            )
            return creds

        except Exception as exc:
            self._audit(
                action="credential.read",
                target=provider_id or "all",
                result="ERROR",
                reason=f"read failed: {exc}"
            )
            # Fail closed on read error
            return {"error": f"CREDENTIAL_READ_FAILED: {exc}"}

    def write_credentials(self, provider_id: str, payload: dict) -> dict[str, Any]:
        """Write credentials to auth.json through HKP-gated broker."""
        identity = self._get_identity()

        # 1. HKP gate
        gate_decision = self._hkp_gate(
            action="credential.write",
            target=provider_id
        )
        if not gate_decision["allowed"]:
            self._audit(
                action="credential.write",
                target=provider_id,
                result="DENIED",
                reason=f"HKP gate blocked: {gate_decision['reason']}"
            )
            return {"success": False, "error": f"BLOCKED_BY_HKP: {gate_decision['reason']}"}

        # 2. Identity check
        if identity not in _CREDENTIAL_PRIVILEGED_IDENTITIES:
            self._audit(
                action="credential.write",
                target=provider_id,
                result="DENIED",
                reason=f"identity '{identity}' not authorized"
            )
            return {"success": False, "error": f"BLOCKED_BY_BROKER: identity '{identity}' not authorized"}

        # 3. Write
        try:
            import hermes_cli.auth as auth_mod
            auth_mod.write_credential_pool(provider_id, payload)
            self._audit(
                action="credential.write",
                target=provider_id,
                result="ALLOWED",
                reason=f"identity={identity}"
            )
            return {"success": True}
        except Exception as exc:
            self._audit(
                action="credential.write",
                target=provider_id,
                result="ERROR",
                reason=f"write failed: {exc}"
            )
            return {"success": False, "error": f"CREDENTIAL_WRITE_FAILED: {exc}"}


# ── Public singleton ───────────────────────────────────────────────────────
_broker_instance: Optional[_CredentialBroker] = None
_broker_lock = threading.Lock()


def _get_broker() -> _CredentialBroker:
    global _broker_instance
    if _broker_instance is None:
        with _broker_lock:
            if _broker_instance is None:
                _broker_instance = _CredentialBroker()
    return _broker_instance


# ── Public API ─────────────────────────────────────────────────────────────

def get_credentials(provider_id: Optional[str] = None) -> dict[str, Any]:
    """Get credentials through the HKP-gated broker."""
    return _get_broker().get_credentials(provider_id)


def write_credentials(provider_id: str, payload: dict) -> dict[str, Any]:
    """Write credentials through the HKP-gated broker."""
    return _get_broker().write_credentials(provider_id, payload)


def identity_allowed() -> bool:
    """Check if current process identity is allowed credential access."""
    return get_process_identity() in _CREDENTIAL_PRIVILEGED_IDENTITIES


def health() -> dict[str, Any]:
    """Return broker health status."""
    try:
        identity = get_process_identity()
        from agent.hkp_enforcer import is_emergency_stop, policy_available
        return {
            "status": "ok" if identity in _CREDENTIAL_PRIVILEGED_IDENTITIES else "degraded",
            "identity": identity,
            "can_access_credentials": identity in _CREDENTIAL_PRIVILEGED_IDENTITIES,
            "hkp_emergency_stop": is_emergency_stop(),
            "hkp_policy_available": policy_available(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }


__all__ = [
    "IDENTITY_HERMES_CORE",
    "IDENTITY_GATEWAY",
    "IDENTITY_CRON",
    "IDENTITY_TOOLS",
    "IDENTITY_WORKFLOW",
    "IDENTITY_EMPLOYEE_PROFILE",
    "IDENTITY_CHILD_PROCESS",
    "IDENTITY_UNKNOWN",
    "get_process_identity",
    "set_process_identity",
    "get_credentials",
    "write_credentials",
    "identity_allowed",
    "health",
]
