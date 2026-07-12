"""HKP Control Plane — typed action contracts, schemas, and validation.

Every request from Hermes runtime to Control Plane uses these contracts.
Phase A: all fields required, validation strict.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# ── Version ───────────────────────────────────────────────────────────────
HKP_VERSION = "hkp-v1"
APPROVAL_TOKEN_VERSION = 1


# ── Action Types ──────────────────────────────────────────────────────────
class ActionType(str, Enum):
    MODEL_INFER = "model.infer"
    MODEL_INFER_BATCH = "model.infer.batch"
    PLATFORM_SEND = "platform.send"
    PLATFORM_UPLOAD = "platform.upload"
    PLATFORM_DELETE = "platform.delete"
    DATA_READ = "data.read"
    DATA_WRITE = "data.write"
    CREDENTIAL_VERIFY = "credential.verify"
    AUDIT_QUERY = "audit.query"
    POLICY_CHECK = "policy.check"


_ACTION_TYPES = frozenset(t.value for t in ActionType)


# ── Request Envelope ──────────────────────────────────────────────────────
@dataclass
class ActionRequest:
    version: str
    request_id: str
    timestamp: str
    caller: dict
    action: dict
    provenance: Optional[dict] = None
    approval: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> ActionRequest:
        return cls(
            version=data.get("version", ""),
            request_id=data.get("request_id", ""),
            timestamp=data.get("timestamp", ""),
            caller=data.get("caller", {}),
            action=data.get("action", {}),
            provenance=data.get("provenance"),
            approval=data.get("approval"),
        )

    def validate(self) -> Optional[str]:
        """Validate the request envelope. Returns error message or None."""
        if self.version != HKP_VERSION:
            return f"unsupported version: {self.version}"
        if not self.request_id or not re.match(r"^[a-zA-Z0-9_-]+$", self.request_id):
            return "invalid or missing request_id"
        if not self.action:
            return "missing action"
        action_type = self.action.get("type", "")
        if action_type not in _ACTION_TYPES:
            return f"unsupported action type: {action_type}"
        return None


# ── Response Envelope ─────────────────────────────────────────────────────
@dataclass
class ActionResponse:
    version: str
    request_id: str
    timestamp: str
    status: str  # "ok", "denied", "error"
    result: Optional[dict] = None
    error: Optional[dict] = None
    audit: Optional[dict] = None

    @classmethod
    def ok(cls, request_id: str, result: dict = None, audit: dict = None) -> ActionResponse:
        return cls(
            version=HKP_VERSION,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="ok",
            result=result or {},
            audit=audit,
        )

    @classmethod
    def denied(cls, request_id: str, code: str, reason: str, policy_class: str = "",
               audit_id: str = "") -> ActionResponse:
        return cls(
            version=HKP_VERSION,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="denied",
            error={"code": code, "reason": reason, "policy_class": policy_class, "audit_id": audit_id},
        )

    @classmethod
    def error(cls, request_id: str, reason: str) -> ActionResponse:
        return cls(
            version=HKP_VERSION,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="error",
            error={"code": "INTERNAL_ERROR", "reason": reason},
        )

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ── Approval Token ────────────────────────────────────────────────────────
@dataclass
class ApprovalToken:
    token: str
    version: int
    expires_at: str
    scope: dict
    approver: str

    def is_valid(self, action_type: str, target: str) -> tuple[bool, str]:
        """Validate token against the requested action. Returns (valid, reason)."""
        if self.version != APPROVAL_TOKEN_VERSION:
            return False, "unsupported token version"
        try:
            expires = datetime.fromisoformat(self.expires_at)
            if expires < datetime.now(timezone.utc):
                return False, "token expired"
        except (ValueError, TypeError):
            return False, "invalid expires_at"
        if self.scope.get("action") != action_type:
            return False, f"token scope action mismatch: {self.scope.get('action')} vs {action_type}"
        if self.scope.get("target") and target and not target.startswith(self.scope["target"]):
            return False, f"token target mismatch"
        return True, ""


__all__ = [
    "HKP_VERSION",
    "ActionType",
    "ActionRequest",
    "ActionResponse",
    "ApprovalToken",
]
