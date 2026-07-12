"""HKP Action Policy Gate v1 enforcement helpers.

This module intentionally covers only the v1 mandatory enforcement points:
cron ``no_agent`` script execution and background memory/skill writes.  It is
not a generic tool-layer policy engine.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

POLICY_RELATIVE_PATH = Path("Specification Layer") / "HKP_ACTION_POLICY_STATE_v1.0.json"
POLICY_ID = "HKP-POL-001"
SCHEMA_VERSION = "1.0"
APPROVED_STATUSES = frozenset({"APPROVED_NOT_ENFORCED", "APPROVED_ENFORCED"})
POLICY_GATE_MARKER = "BLOCKED_BY_HKP_POLICY_GATE"
POLICY_GATE_ALLOWED_MARKER = "ALLOWED_BY_HKP_POLICY_GATE"
VOICE_BOT_POLLER_JOB_ID = "787534815e81"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    policy_class: str
    reason: str


@dataclass(frozen=True)
class HKPPolicyGate:
    policy_path: Path
    valid: bool
    status: str
    allowlisted_critical_runtime: frozenset[str]
    background_review_status: str
    load_error: str = ""

    @property
    def failure_reason(self) -> str:
        if self.valid:
            return ""
        return self.load_error or "policy state invalid"

    def observe_only_allowed(self) -> PolicyDecision:
        return PolicyDecision(
            True,
            "OBSERVE_ONLY",
            "OBSERVE_ONLY remains permitted when policy side-effect gates fail closed",
        )

    def decide_no_agent_job(self, job: Mapping[str, Any]) -> PolicyDecision:
        if not self.valid:
            return PolicyDecision(
                False,
                "DENY",
                f"policy state invalid: {self.failure_reason}",
            )
        if job.get("enabled") is not True:
            return PolicyDecision(False, "DENY", "job is disabled")
        job_id = job.get("id")
        if job_id != VOICE_BOT_POLLER_JOB_ID:
            return PolicyDecision(
                False,
                "QUARANTINED",
                "no_agent job is not the voice bot poller runtime",
            )
        if VOICE_BOT_POLLER_JOB_ID in self.allowlisted_critical_runtime:
            return PolicyDecision(
                True,
                "ALLOWLISTED_CRITICAL_RUNTIME",
                "job id is allowlisted critical runtime",
            )
        return PolicyDecision(
            False,
            "QUARANTINED",
            "no_agent job is not in allowlisted_critical_runtime",
        )

    def decide_background_review(self) -> PolicyDecision:
        if not self.valid:
            return PolicyDecision(
                False,
                "DENY",
                f"policy state invalid: {self.failure_reason}",
            )
        return PolicyDecision(
            False,
            "QUARANTINED",
            f"background_review status is {self.background_review_status or 'QUARANTINED'}",
        )

    def decide_background_canonical_write(self, target: str) -> PolicyDecision:
        bg_decision = self.decide_background_review()
        if not bg_decision.allowed:
            return PolicyDecision(
                False,
                bg_decision.policy_class,
                f"background_review canonical write denied for {target}: {bg_decision.reason}",
            )
        return PolicyDecision(
            False,
            "QUARANTINED",
            f"background_review canonical write denied for {target}",
        )


_POLICY_GATE: Optional[HKPPolicyGate] = None


def _invalid_gate(policy_path: Path, reason: str) -> HKPPolicyGate:
    return HKPPolicyGate(
        policy_path=policy_path,
        valid=False,
        status="",
        allowlisted_critical_runtime=frozenset(),
        background_review_status="",
        load_error=reason,
    )


def _load_policy_gate() -> HKPPolicyGate:
    root_value = os.environ.get("HKP_AUTHORITY_ROOT", "").strip()
    if not root_value:
        return _invalid_gate(POLICY_RELATIVE_PATH, "HKP_AUTHORITY_ROOT is not set")

    root = Path(root_value).expanduser()
    policy_path = root / POLICY_RELATIVE_PATH
    try:
        resolved_root = root.resolve(strict=False)
        resolved_policy = policy_path.resolve(strict=False)
    except OSError as exc:
        return _invalid_gate(policy_path, f"failed to resolve policy path: {exc}")

    expected_policy = resolved_root / POLICY_RELATIVE_PATH
    if resolved_policy != expected_policy:
        return _invalid_gate(policy_path, "policy path does not match HKP_AUTHORITY_ROOT exact policy location")

    try:
        raw = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _invalid_gate(policy_path, f"policy file unreadable: {exc}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _invalid_gate(policy_path, f"policy file invalid JSON: {exc}")

    if not isinstance(data, dict):
        return _invalid_gate(policy_path, "policy root is not an object")

    policy_id = data.get("policy_id")
    if not isinstance(policy_id, str):
        return _invalid_gate(policy_path, f"policy_id is not {POLICY_ID}")
    if policy_id != POLICY_ID:
        return _invalid_gate(policy_path, f"policy_id is not {POLICY_ID}")

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str):
        return _invalid_gate(policy_path, f"schema_version is not {SCHEMA_VERSION}")
    if schema_version != SCHEMA_VERSION:
        return _invalid_gate(policy_path, f"schema_version is not {SCHEMA_VERSION}")

    status = data.get("status")
    if not isinstance(status, str):
        return _invalid_gate(policy_path, "policy status is not approved")
    if status not in APPROVED_STATUSES:
        return _invalid_gate(policy_path, "policy status is not approved")

    entries = data.get("allowlisted_critical_runtime")
    if not isinstance(entries, list):
        return _invalid_gate(policy_path, "allowlisted_critical_runtime is missing or malformed")
    if len(entries) != 1:
        return _invalid_gate(policy_path, "allowlisted_critical_runtime must contain exactly one entry")
    entry = entries[0]
    if not isinstance(entry, dict):
        return _invalid_gate(policy_path, "allowlisted_critical_runtime[0] is not an object")
    allowlisted_job_id = entry.get("job_id")
    if not isinstance(allowlisted_job_id, str):
        return _invalid_gate(policy_path, "allowlisted_critical_runtime[0].job_id is not the voice bot poller")
    if allowlisted_job_id != VOICE_BOT_POLLER_JOB_ID:
        return _invalid_gate(policy_path, "allowlisted_critical_runtime[0].job_id is not the voice bot poller")

    lockdown = data.get("governance_lockdown_status")
    if not isinstance(lockdown, dict):
        return _invalid_gate(policy_path, "governance_lockdown_status is missing or malformed")
    background_status = lockdown.get("background_review")
    if not isinstance(background_status, str):
        return _invalid_gate(policy_path, "governance_lockdown_status.background_review is not DISABLED")
    if background_status != "DISABLED":
        return _invalid_gate(policy_path, "governance_lockdown_status.background_review is not DISABLED")

    return HKPPolicyGate(
        policy_path=resolved_policy,
        valid=True,
        status=status,
        allowlisted_critical_runtime=frozenset({allowlisted_job_id}),
        background_review_status=background_status,
    )


def get_policy_gate() -> HKPPolicyGate:
    """Return the process-frozen policy gate snapshot, loading at most once."""
    global _POLICY_GATE
    if _POLICY_GATE is None:
        _POLICY_GATE = _load_policy_gate()
    return _POLICY_GATE


def reset_policy_gate_for_tests() -> None:
    global _POLICY_GATE
    _POLICY_GATE = None


def observe_only_allowed() -> PolicyDecision:
    return get_policy_gate().observe_only_allowed()


def log_blocked_by_policy_gate(
    logger_obj: logging.Logger,
    *,
    job_id: str = "",
    policy_class: str,
    reason: str,
    target: str = "",
) -> None:
    logger_obj.warning(
        "%s job_id=%s target=%s policy_class=%s reason=%s",
        POLICY_GATE_MARKER,
        job_id or "N/A",
        target or "N/A",
        policy_class,
        reason,
    )
