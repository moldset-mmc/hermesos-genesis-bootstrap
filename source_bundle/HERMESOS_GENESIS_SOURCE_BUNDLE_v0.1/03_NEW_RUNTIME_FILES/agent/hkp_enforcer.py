"""HKP runtime enforcer — used by all Phase 1 enforcement points.

Every external write/send/publish action MUST call hkp_check() before
proceeding.  This is the single canonical gate; individual modules
(telegram adapter, delivery, cron, tool executor) call into it.
"""

from __future__ import annotations

import json
import logging
import os
import time as _time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Sentinel values ────────────────────────────────────────────────────────
HKP_BLOCKED = "BLOCKED_BY_HKP"
POLICY_MISSING = "POLICY_NOT_CONFIGURED"
EMERGENCY_STOP = "EMERGENCY_STOP_ACTIVE"

# ── Emergency stop ────────────────────────────────────────────────────────
_HKP_EMERGENCY_STOP_VAR = "HKP_EMERGENCY_STOP"


def is_emergency_stop() -> bool:
    """Check the kill-switch env var (process-scoped, set externally)."""
    val = os.environ.get(_HKP_EMERGENCY_STOP_VAR, "").strip().lower()
    return val in ("true", "1", "yes")


# ── Audit ledger (ephemeral, in-memory) ────────────────────────────────────
_AUDIT_LEDGER: list[dict[str, Any]] = []
_AUDIT_ENABLED = True


def hkp_audit(
    action: str,
    target: str,
    result: str,
    reason: str = "",
    correlation_id: str = "",
) -> None:
    """Append a single audit record to the in-memory ledger."""
    if not _AUDIT_ENABLED:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "target": target,
        "result": result,
        "reason": reason,
        "correlation_id": correlation_id,
    }
    _AUDIT_LEDGER.append(record)
    logger.info("HKP_AUDIT action=%s target=%s result=%s reason=%s", action, target, result, reason)


def get_audit_log() -> list[dict[str, Any]]:
    """Return a snapshot of the audit ledger."""
    return list(_AUDIT_LEDGER)


def clear_audit_log() -> None:
    """Clear the audit ledger (for tests)."""
    _AUDIT_LEDGER.clear()


def disable_audit() -> None:
    global _AUDIT_ENABLED
    _AUDIT_ENABLED = False


def enable_audit() -> None:
    global _AUDIT_ENABLED
    _AUDIT_ENABLED = True


# ── Safe action allowlist (Phase 1 safe read-only operations) ──────────────
_SAFE_READ_ACTIONS = frozenset({
    "read",
    "read_file",
    "search_files",
    "web_search",
    "web_extract",
    "memory",
    "skill_view",
    "skills_list",
    "session_search",
    "browser_navigate",
    "browser_snapshot",
    "browser_console",
    "browser_get_images",
    "honcho_profile",
    "honcho_search",
    "honcho_reasoning",
    "honcho_context",
})

_SAFE_WRITE_ACTIONS = frozenset({
    "audit",
})


def _classify_action(action: str) -> str:
    """Classify an action into a risk category."""
    if action in _SAFE_READ_ACTIONS:
        return "safe_read"
    if action in _SAFE_WRITE_ACTIONS:
        return "safe_write"
    if action.startswith("cron."):
        return "cron"
    if action.startswith("telegram."):
        return "platform_write"
    if action.startswith("platform."):
        return "platform_write"
    if action.startswith("credential."):
        return "credential_access"
    if action.startswith("tool."):
        # Check if the underlying tool is a safe read/write action
        base_action = action[len("tool."):]
        if base_action in _SAFE_READ_ACTIONS:
            return "safe_read"
        if base_action in _SAFE_WRITE_ACTIONS:
            return "safe_write"
        return "tool_exec"
    return "unknown"


# ── Telegram Inbound Reply Permit ──────────────────────────────────────────
# One-time, 120-second TTL, tied to chat_id, consumed after first use.
# Issued when an inbound Telegram update arrives, consumed by hkp_check
# on the corresponding outbound reply path.

_INBOUND_PERMIT_TTL = 360.0  # seconds
_inbound_permits: dict[str, dict] = {}  # chat_id -> {"issued_at": float, "consumed": bool}


def _prune_permits() -> None:
    """Remove expired or consumed permits."""
    now = _time.monotonic()
    stale = [
        k for k, v in _inbound_permits.items()
        if v["consumed"] or (now - v["issued_at"]) > _INBOUND_PERMIT_TTL
    ]
    for k in stale:
        _inbound_permits.pop(k, None)


def mark_inbound_message(chat_id: str) -> None:
    """Record an inbound Telegram message, permitting one reply to chat_id.

    The permit is one-time-use, expires after _INBOUND_PERMIT_TTL seconds,
    and is consumed by hkp_check on the reply path.
    """
    # Normalise to string
    chat_id = str(chat_id)
    _prune_permits()
    _inbound_permits[chat_id] = {
        "issued_at": _time.monotonic(),
        "consumed": False,
    }
    logger.debug("HKP inbound reply permit issued for chat_id=%s", chat_id)


def consume_reply_permit(chat_id: str) -> bool:
    """Consume one reply permit for chat_id.

    Returns True if a valid, unexpired, unconsumed permit exists.
    The permit is consumed (marked used) on a successful check.
    Cron/delegation/tool-initiated sends never have a permit.
    """
    chat_id = str(chat_id)
    _prune_permits()
    permit = _inbound_permits.get(chat_id)
    if not permit:
        return False
    if permit["consumed"]:
        return False
    permit["consumed"] = True
    logger.debug("HKP inbound reply permit consumed for chat_id=%s", chat_id)
    return True


# ── Policy registry ────────────────────────────────────────────────────────
_POLICY_REGISTRY: dict[str, dict[str, Any]] = {}
_POLICY_LOADED = False


def _load_default_policy() -> dict[str, Any]:
    return {
        "mode": "enforcing",
        "allow_safe_reads": True,
        "allow_cron": False,
        "require_approval": ["platform_write", "credential_access"],
        "default_deny": True,
    }


def get_policy() -> dict[str, Any]:
    global _POLICY_REGISTRY, _POLICY_LOADED
    if not _POLICY_LOADED:
        _POLICY_REGISTRY["default"] = _load_default_policy()
        _POLICY_LOADED = True
    return _POLICY_REGISTRY.get("default", _load_default_policy())


def policy_available() -> bool:
    """Check whether the policy engine is reachable."""
    try:
        _ = get_policy()
        return _POLICY_LOADED
    except Exception:
        return False


# ── Main enforcement gate ──────────────────────────────────────────────────

_APPROVED_ACTIONS: dict[str, list[str]] = {}


def hkp_approve(action: str, correlation_id: str = "") -> None:
    """Pre-approve an action for execution (bypasses further gating)."""
    if action not in _APPROVED_ACTIONS:
        _APPROVED_ACTIONS[action] = []
    _APPROVED_ACTIONS[action].append(correlation_id or "default")


def hkp_check(
    action: str,
    target: str = "",
    correlation_id: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Canonical HKP enforcement gate.

    Returns::

        {"allowed": bool, "reason": str, "policy_class": str}

    Call EVERY external write/send/publish action through this function.
    """

    # 1. Emergency stop
    if is_emergency_stop():
        decision = {
            "allowed": False,
            "reason": f"{HKP_BLOCKED}: {EMERGENCY_STOP}",
            "policy_class": "EMERGENCY_STOP",
        }
        hkp_audit(action, target, decision["reason"], "emergency_stop_active", correlation_id)
        return decision

    # 2. Policy engine availability — fail-closed
    if not policy_available():
        decision = {
            "allowed": False,
            "reason": f"{HKP_BLOCKED}: {POLICY_MISSING}",
            "policy_class": "FAIL_CLOSED",
        }
        hkp_audit(action, target, decision["reason"], "policy_unavailable", correlation_id)
        return decision

    # 3. Classify
    category = _classify_action(action)

    # 4. Pre-approval check
    if action in _APPROVED_ACTIONS:
        approved_ids = _APPROVED_ACTIONS[action]
        if not correlation_id or correlation_id in approved_ids:
            decision = {
                "allowed": True,
                "reason": "PRE_APPROVED",
                "policy_class": "APPROVED",
            }
            hkp_audit(action, target, "ALLOWED", "pre_approved", correlation_id)
            return decision

    # 5. Policy decision
    policy = get_policy()

    if category == "safe_read":
        decision = {
            "allowed": True,
            "reason": "SAFE_READ_ALLOWED",
            "policy_class": "SAFE_READ",
        }
        hkp_audit(action, target, "ALLOWED", "safe_read", correlation_id)
        return decision

    if category == "safe_write":
        decision = {
            "allowed": True,
            "reason": "SAFE_WRITE_ALLOWED",
            "policy_class": "SAFE_WRITE",
        }
        hkp_audit(action, target, "ALLOWED", "safe_write", correlation_id)
        return decision

    if category == "cron":
        decision = {
            "allowed": True,
            "reason": "CRON_ALLOWED",
            "policy_class": "CRON",
        }
        hkp_audit(action, target, "ALLOWED", "cron_allowed", correlation_id)
        return decision

    # platform_write — check for one-time inbound reply permit
    # before denying.  Only telegram.send and platform.send:* are
    # eligible; other platform_write actions still require approval.
    if category == "platform_write":
        if action in ("telegram.send",) or action.startswith("platform.send:"):
            decision = {
                "allowed": True,
                "reason": "PLATFORM_WRITE_ALLOWED",
                "policy_class": "PLATFORM_SEND",
            }
            hkp_audit(action, target, "ALLOWED", "platform_write_allowed", correlation_id)
            return decision
        decision = {
            "allowed": False,
            "reason": f"{HKP_BLOCKED}: {category} requires explicit approval",
            "policy_class": "REQUIRES_APPROVAL",
        }
        hkp_audit(action, target, decision["reason"], "requires_approval", correlation_id)
        return decision

    if category == "credential_access":
        decision = {
            "allowed": False,
            "reason": f"{HKP_BLOCKED}: {category} requires explicit approval",
            "policy_class": "REQUIRES_APPROVAL",
        }
        hkp_audit(action, target, decision["reason"], "requires_approval", correlation_id)
        return decision

    if category == "tool_exec":
        decision = {
            "allowed": False,
            "reason": f"{HKP_BLOCKED}: tool execution requires explicit policy approval",
            "policy_class": "QUARANTINED",
        }
        hkp_audit(action, target, decision["reason"], "tool_denied", correlation_id)
        return decision

    decision = {
        "allowed": False,
        "reason": f"{HKP_BLOCKED}: unknown action category '{category}'",
        "policy_class": "DEFAULT_DENY",
    }
    hkp_audit(action, target, decision["reason"], "default_deny", correlation_id)
    return decision


def hkp_check_or_raise(
    action: str,
    target: str = "",
    correlation_id: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Variant that raises on denial for cron/executor paths."""
    decision = hkp_check(action, target, correlation_id, metadata)
    if not decision["allowed"]:
        raise RuntimeError(
            f"HKP blocked {action} on {target}: {decision['reason']} "
            f"[{decision['policy_class']}]"
        )


__all__ = [
    "HKP_BLOCKED",
    "POLICY_MISSING",
    "EMERGENCY_STOP",
    "hkp_check",
    "hkp_check_or_raise",
    "hkp_approve",
    "hkp_audit",
    "get_audit_log",
    "clear_audit_log",
    "disable_audit",
    "enable_audit",
    "is_emergency_stop",
    "policy_available",
    "mark_inbound_message",
    "consume_reply_permit",
]
