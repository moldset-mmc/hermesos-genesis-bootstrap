"""HKP Policy Engine — rule evaluation and approval validation.

Phase A: Foundation/shadow mode.
  - Policy registry with default rules (inherit from hkp_enforcer).
  - Approval token validation.
  - Phase A: all actions are ALLOWED (shadow/passthrough mode).
  - Phase B: enforcement enables.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .audit_ledger import audit_event, get_ledger

logger = logging.getLogger("HKP.PolicyEngine")

# ── Policy actions that require approval ──────────────────────────────────
APPROVAL_REQUIRED_ACTIONS = frozenset({
    "platform.send",
    "platform.upload",
    "platform.delete",
    "model.infer.batch",
    "data.write",
})

# Phase A: emergency stop forces denial regardless of mode
EMERGENCY_STOP_VAR = "HKP_EMERGENCY_STOP"


def _is_emergency_stop() -> bool:
    val = os.environ.get(EMERGENCY_STOP_VAR, "").strip().lower()
    return val in ("true", "1", "yes")


class PolicyEngine:
    """HKP Policy Engine — evaluate action requests against policy rules.

    Phase A: shadow mode only.  All actions produce ALLOWED + audit,
    unless emergency stop is active (which DENIES).
    """

    def __init__(self, mode: str = "shadow"):
        self.mode = mode  # "shadow" (Phase A) or "enforcing" (Phase B+)

    def evaluate(self, action_type: str, target: str, caller: dict,
                 approval_token: Optional[dict] = None) -> dict:
        """Evaluate a single action request against policy.

        Returns: {"allowed": bool, "reason": str, "policy_class": str}
        """
        request_id = caller.get("request_id", "unknown")

        # 1. Emergency stop — DENIES everything
        if _is_emergency_stop():
            audit_event(action_type, target, "DENIED", "EMERGENCY_STOP_ACTIVE",
                        request_id=request_id, policy_class="EMERGENCY_STOP")
            return {"allowed": False, "reason": "EMERGENCY_STOP_ACTIVE", "policy_class": "EMERGENCY_STOP"}

        # 2. Shadow mode — ALLOW + audit (Phase A passthrough)
        if self.mode == "shadow":
            audit_event(action_type, target, "ALLOWED_SHADOW",
                        f"shadow mode (Phase A): action allowed, policy not enforced",
                        request_id=request_id, policy_class="SHADOW_PASSTHROUGH")
            return {"allowed": True, "reason": "SHADOW_MODE_PASSTHROUGH", "policy_class": "SHADOW_PASSTHROUGH"}

        # 3. Enforcing mode (Phase B+) — full policy check
        if self.mode == "enforcing":
            # Check approval requirement
            if action_type in APPROVAL_REQUIRED_ACTIONS:
                if not approval_token:
                    audit_event(action_type, target, "DENIED",
                                "approval required but no token provided",
                                request_id=request_id, policy_class="APPROVAL_REQUIRED")
                    return {"allowed": False, "reason": "approval required", "policy_class": "APPROVAL_REQUIRED"}

                # Validate token
                from .schema import ApprovalToken
                token = ApprovalToken(**approval_token)
                valid, err_reason = token.is_valid(action_type, target)
                if not valid:
                    audit_event(action_type, target, "DENIED", f"invalid token: {err_reason}",
                                request_id=request_id, policy_class="TOKEN_INVALID")
                    return {"allowed": False, "reason": f"invalid token: {err_reason}",
                            "policy_class": "TOKEN_INVALID"}

            # Passed all checks
            audit_event(action_type, target, "ALLOWED",
                        "policy enforcement passed",
                        request_id=request_id, policy_class="ALLOWED")
            return {"allowed": True, "reason": "policy passed", "policy_class": "ALLOWED"}

        # Unknown mode — fail closed
        audit_event(action_type, target, "DENIED", f"unknown policy mode: {self.mode}",
                    request_id=request_id, policy_class="FAIL_CLOSED")
        return {"allowed": False, "reason": f"unknown policy mode: {self.mode}",
                "policy_class": "FAIL_CLOSED"}


# ── Singleton ─────────────────────────────────────────────────────────────
_engine: Optional[PolicyEngine] = None


def get_engine(mode: str = "shadow") -> PolicyEngine:
    global _engine
    if _engine is None:
        _engine = PolicyEngine(mode=mode)
    return _engine


def check_action(action_type: str, target: str, caller: dict,
                 approval_token: Optional[dict] = None) -> dict:
    """Convenience: evaluate action against policy."""
    return get_engine().evaluate(action_type, target, caller, approval_token)
