"""Deterministic user-facing Hermes governance status responses."""

from __future__ import annotations

import json
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

CANONICAL_HKP_ROOT = Path(os.environ.get("HKP_AUTHORITY_ROOT", ""))
POLICY_RELATIVE_PATH = Path("Specification Layer") / "HKP_ACTION_POLICY_STATE_v1.0.json"
INTEGRITY_MANIFEST_FILENAME = "HKP_INTEGRITY_MANIFEST_v1.3.json"
CRON_JOBS_RELATIVE_PATH = Path("cron") / "jobs.json"
CONFIG_FILENAME = "config.yaml"

POLICY_ID = "HKP-POL-001"
POLICY_SCHEMA_VERSION = "1.0"
POLICY_ENFORCED_STATUS = "APPROVED_ENFORCED"
INTEGRITY_MANIFEST_ID = "HKP-INT-004"
INTEGRITY_MANIFEST_SCHEMA_VERSION = "1.3"
BACKGROUND_REVIEW_DISABLED = "DISABLED"
VOICE_BOT_POLLER_JOB_ID = "787534815e81"
_LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HKP_INT_004_SOURCE_PATHS = (
    "README.md",
    "HKP_INDEX.md",
    "DOCUMENT_REGISTRY.md",
    "HKP_DEPENDENCY_MAP.md",
    "HKP_AUDIT_REPORT.md",
    "01_Hermes_OS_Architectural_Level_1/GENESIS_000.txt",
    "HERMES_OS_CORE_FOUNDATION_INDEX_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_GLOSSARY_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_CONSTITUTION_v1.0.docx",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_OPERATING_MODEL_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_REGISTRY_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_BOOTSTRAP_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_ARCHITECTURE_DECISIONS_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_FOUNDATION_RELEASE_1.0_CANONICAL_RESOLUTION.docx",
    "Operating Layer/HERMES_OWNER_OPERATING_PROFILE_v1.0.md",
    "Operating Layer/HKP_PRODUCTION_BASELINE_RC2_1.md",
    "Specification Layer/HKP_ACTION_POLICY_GATE_SPEC_v1.0.md",
    "Specification Layer/HKP_ACTION_POLICY_STATE_v1.0.json",
)
_HKP_INT_004_SOURCE_PATH_SET = frozenset(_HKP_INT_004_SOURCE_PATHS)

_STATUS_REQUESTS = frozenset(
    {
        "покажи состояние и политику hermes",
        "статус hermes",
        "состояние hermes",
        "какая у тебя политика",
    }
)
_DIAGNOSTIC_REQUEST = "диагностика hermes"
_CONNECTED_STATES = frozenset({"connected", "running", "ready", "ok", "healthy"})
_RUNNING_GATEWAY_STATES = frozenset({"running", "degraded"})


@dataclass(frozen=True)
class GovernanceSnapshot:
    policy_gate_active: bool
    voice_poller_allowed: bool
    hkp_integrity_verified: bool
    background_review_disabled: bool
    quarantined_no_agent_count: int
    policy_status: str
    policy_schema_version: str
    policy_id: str
    manifest_schema_version: str
    manifest_id: str
    policy_load_state: str
    manifest_load_state: str
    cron_load_state: str
    config_load_state: str


@dataclass(frozen=True)
class RuntimeProbe:
    system_working: bool
    voice_receiver_working: bool
    gateway_state: str
    platform_state: str
    source: str


def normalize_governance_status_request(text: str | None) -> str:
    """Normalize a short Russian governance status request for exact matching."""
    normalized = (text or "").strip().casefold().replace("ё", "е")
    normalized = re.sub(r"[?!.,;:]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def is_governance_status_request(text: str | None) -> bool:
    return normalize_governance_status_request(text) in _STATUS_REQUESTS


def is_governance_diagnostic_request(text: str | None) -> bool:
    return normalize_governance_status_request(text) == _DIAGNOSTIC_REQUEST


def _hkp_root() -> Path:
    override = os.getenv("HKP_AUTHORITY_ROOT")
    if override and override.strip():
        return Path(override.strip()).expanduser()
    return CANONICAL_HKP_ROOT


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home()
    except Exception:
        return Path.home() / ".hermes"


def _load_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, "unreadable"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "invalid_root"
    return payload, "loaded"


def _load_yaml_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, "unreadable"
    try:
        import yaml

        payload = yaml.safe_load(raw) or {}
    except Exception:
        return None, "invalid_yaml"
    if not isinstance(payload, dict):
        return None, "invalid_root"
    return payload, "loaded"


def _strict_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _policy_allowlists_voice_poller(policy_data: Mapping[str, Any] | None) -> bool:
    if not isinstance(policy_data, Mapping):
        return False
    allowlisted = policy_data.get("allowlisted_critical_runtime")
    if not isinstance(allowlisted, list) or len(allowlisted) != 1:
        return False
    entry = allowlisted[0]
    if not isinstance(entry, dict):
        return False
    job_id = entry.get("job_id")
    return isinstance(job_id, str) and job_id == VOICE_BOT_POLLER_JOB_ID


def _policy_identity_valid(policy_data: Mapping[str, Any] | None) -> bool:
    if not isinstance(policy_data, Mapping):
        return False
    return (
        policy_data.get("policy_id") == POLICY_ID
        and policy_data.get("schema_version") == POLICY_SCHEMA_VERSION
    )


def _runtime_jobs_snapshot(
    jobs_payload: Mapping[str, Any] | None,
) -> tuple[bool, int]:
    if not isinstance(jobs_payload, Mapping):
        return False, 0
    jobs = jobs_payload.get("jobs")
    if not isinstance(jobs, list):
        return False, 0

    voice_poller_enabled = False
    quarantined_no_agent_count = 0
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_id = job.get("id")
        if job_id == VOICE_BOT_POLLER_JOB_ID and job.get("enabled") is True:
            voice_poller_enabled = True
        if (
            job.get("no_agent") is True
            and job.get("state") == "quarantined"
            and job_id != VOICE_BOT_POLLER_JOB_ID
        ):
            quarantined_no_agent_count += 1
    return voice_poller_enabled, quarantined_no_agent_count


def _legacy_allowlist_permits_voice_poller(config_data: Mapping[str, Any] | None) -> bool:
    if not isinstance(config_data, Mapping):
        return False
    cron_cfg = config_data.get("cron")
    if not isinstance(cron_cfg, dict):
        return False
    quarantine = cron_cfg.get("no_agent_quarantine")
    if not isinstance(quarantine, dict):
        return False
    if quarantine.get("enabled") is not True:
        return False

    allowlist = quarantine.get("allowlist")
    if not isinstance(allowlist, list):
        return False
    return any(
        isinstance(item, str) and item == VOICE_BOT_POLLER_JOB_ID
        for item in allowlist
    )


def _manifest_integrity_verified(
    root: Path,
    manifest_data: Mapping[str, Any] | None,
    manifest_load_state: str,
) -> bool:
    if manifest_load_state != "loaded" or not isinstance(manifest_data, Mapping):
        return False
    if not (
        isinstance(manifest_data.get("manifest_id"), str)
        and manifest_data.get("manifest_id") == INTEGRITY_MANIFEST_ID
    ):
        return False
    if not (
        isinstance(manifest_data.get("schema_version"), str)
        and manifest_data.get("schema_version") == INTEGRITY_MANIFEST_SCHEMA_VERSION
    ):
        return False
    sources = manifest_data.get("sources")
    if not isinstance(sources, list) or len(sources) != len(_HKP_INT_004_SOURCE_PATHS):
        return False

    try:
        resolved_root = root.resolve(strict=True)
    except OSError:
        return False

    manifest_paths: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            return False
        relative_path = source.get("path")
        expected_hash = source.get("sha256")
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or not isinstance(expected_hash, str)
            or not _LOWER_SHA256_RE.fullmatch(expected_hash)
        ):
            return False
        manifest_paths.append(relative_path)

    if len(set(manifest_paths)) != len(manifest_paths):
        return False
    manifest_path_set = frozenset(manifest_paths)
    if manifest_path_set != _HKP_INT_004_SOURCE_PATH_SET:
        return False
    if POLICY_RELATIVE_PATH.as_posix() not in manifest_path_set:
        return False

    for source in sources:
        relative_path = source["path"]
        expected_hash = source["sha256"]
        source_path = root / relative_path
        try:
            resolved_source = source_path.resolve(strict=True)
            resolved_source.relative_to(resolved_root)
        except (OSError, ValueError):
            return False
        try:
            data = source_path.read_bytes()
        except OSError:
            return False
        if hashlib.sha256(data).hexdigest() != expected_hash:
            return False
    return True


def load_governance_snapshot() -> GovernanceSnapshot:
    """Load the read-only runtime facts used by the four-line status response."""
    root = _hkp_root()
    hermes_home = _hermes_home()
    policy_data, policy_load_state = _load_json_object(root / POLICY_RELATIVE_PATH)
    manifest_data, manifest_load_state = _load_json_object(
        root / INTEGRITY_MANIFEST_FILENAME
    )
    jobs_data, cron_load_state = _load_json_object(hermes_home / CRON_JOBS_RELATIVE_PATH)
    config_data, config_load_state = _load_yaml_object(hermes_home / CONFIG_FILENAME)

    policy_payload = policy_data or {}
    policy_id = _strict_text(policy_payload, "policy_id")
    policy_schema = _strict_text(policy_payload, "schema_version")
    policy_status = _strict_text(policy_payload, "status")

    lockdown = policy_payload.get("governance_lockdown_status")
    background_review = (
        lockdown.get("background_review")
        if isinstance(lockdown, dict) and isinstance(lockdown.get("background_review"), str)
        else ""
    )

    policy_allowlists_voice_poller = _policy_allowlists_voice_poller(policy_data)
    hkp_allowlist_permits_voice_poller = (
        policy_load_state == "loaded"
        and _policy_identity_valid(policy_data)
        and policy_allowlists_voice_poller
    )

    voice_poller_enabled, quarantined_no_agent_count = _runtime_jobs_snapshot(jobs_data)
    legacy_allowlist_permits_voice_poller = _legacy_allowlist_permits_voice_poller(
        config_data
    )

    manifest_payload = manifest_data or {}
    manifest_schema = _strict_text(manifest_payload, "schema_version")
    manifest_id = _strict_text(manifest_payload, "manifest_id")

    policy_gate_active = (
        policy_load_state == "loaded"
        and policy_id == POLICY_ID
        and policy_schema == POLICY_SCHEMA_VERSION
        and policy_status == POLICY_ENFORCED_STATUS
        and isinstance(lockdown, dict)
        and background_review == BACKGROUND_REVIEW_DISABLED
        and policy_allowlists_voice_poller
    )
    voice_poller_allowed = (
        policy_gate_active
        and cron_load_state == "loaded"
        and config_load_state == "loaded"
        and voice_poller_enabled
        and legacy_allowlist_permits_voice_poller
        and hkp_allowlist_permits_voice_poller
    )
    hkp_integrity_verified = _manifest_integrity_verified(
        root,
        manifest_data,
        manifest_load_state,
    )
    background_review_disabled = background_review == BACKGROUND_REVIEW_DISABLED

    return GovernanceSnapshot(
        policy_gate_active=policy_gate_active,
        voice_poller_allowed=voice_poller_allowed,
        hkp_integrity_verified=hkp_integrity_verified,
        background_review_disabled=background_review_disabled,
        quarantined_no_agent_count=quarantined_no_agent_count,
        policy_status=policy_status,
        policy_schema_version=policy_schema,
        policy_id=policy_id,
        manifest_schema_version=manifest_schema,
        manifest_id=manifest_id,
        policy_load_state=policy_load_state,
        manifest_load_state=manifest_load_state,
        cron_load_state=cron_load_state,
        config_load_state=config_load_state,
    )


def _runtime_status_payload() -> Mapping[str, Any] | None:
    try:
        from gateway.status import read_runtime_status

        payload = read_runtime_status()
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def probe_runtime_status(
    *,
    source_platform: str | None = None,
    live_platform_states: Mapping[str, bool] | None = None,
) -> RuntimeProbe:
    """Probe runtime status without falling back to memories or prompt text."""
    platform_key = (source_platform or "").strip().lower()
    live_platform_states = live_platform_states or {}

    live_state = None
    if platform_key:
        live_state = live_platform_states.get(platform_key)
    if live_state is None and live_platform_states:
        live_state = any(bool(value) for value in live_platform_states.values())

    payload = _runtime_status_payload()
    gateway_state = ""
    platform_state = ""
    status_probe_ok = False
    platform_probe_ok = False
    if payload is not None:
        gateway_state = str(payload.get("gateway_state") or "").strip().lower()
        status_probe_ok = gateway_state in _RUNNING_GATEWAY_STATES
        platforms = payload.get("platforms")
        if isinstance(platforms, dict) and platform_key:
            platform_payload = platforms.get(platform_key)
            if isinstance(platform_payload, dict):
                platform_state = str(platform_payload.get("state") or "").strip().lower()
                platform_probe_ok = platform_state in _CONNECTED_STATES

    live_probe_ok = live_state is True
    system_working = bool(status_probe_ok or live_probe_ok)
    voice_receiver_working = bool(platform_probe_ok or live_probe_ok)

    source = "unavailable"
    if live_probe_ok:
        source = "live_adapter"
    elif payload is not None:
        source = "runtime_status"

    return RuntimeProbe(
        system_working=system_working,
        voice_receiver_working=voice_receiver_working,
        gateway_state=gateway_state,
        platform_state=platform_state,
        source=source,
    )


def _deviation_line(snapshot: GovernanceSnapshot) -> str:
    if not snapshot.policy_gate_active:
        return "policy state не подтвержден"
    if not snapshot.hkp_integrity_verified:
        return "HKP manifest не подтвержден"
    if not snapshot.background_review_disabled:
        return "background review не подтвержден"
    return "нет"


def render_governance_status(
    *,
    source_platform: str | None = None,
    live_platform_states: Mapping[str, bool] | None = None,
) -> str:
    snapshot = load_governance_snapshot()
    policy_gate = "ACTIVE" if snapshot.policy_gate_active else "FAIL"
    voice_poller = "ALLOWED" if snapshot.voice_poller_allowed else "FAIL"
    integrity = "VERIFIED" if snapshot.hkp_integrity_verified else "FAIL"
    return (
        f"Policy Gate: {policy_gate}\n"
        f"Voice poller: {voice_poller}\n"
        f"Other no_agent jobs: {snapshot.quarantined_no_agent_count} QUARANTINED\n"
        f"Integrity HKP-INT-004: {integrity}"
    )


def render_governance_diagnostic(
    *,
    source_platform: str | None = None,
    live_platform_states: Mapping[str, bool] | None = None,
) -> str:
    snapshot = load_governance_snapshot()
    runtime = probe_runtime_status(
        source_platform=source_platform,
        live_platform_states=live_platform_states,
    )
    policy_state = "OK" if snapshot.policy_gate_active else "CHECK"
    manifest_state = "OK" if snapshot.hkp_integrity_verified else "CHECK"
    runtime_state = "OK" if runtime.system_working else "CHECK"
    voice_state = "OK" if runtime.voice_receiver_working else "CHECK"
    gateway_state = runtime.gateway_state or "unavailable"
    platform_state = runtime.platform_state or "unavailable"

    return (
        "HERMES — ДИАГНОСТИКА\n\n"
        f"Policy state: {policy_state}; id={snapshot.policy_id or 'missing'}; "
        f"status={snapshot.policy_status or 'missing'}; "
        f"schema={snapshot.policy_schema_version or 'missing'}; "
        f"load={snapshot.policy_load_state}\n"
        f"Integrity manifest: {manifest_state}; id={snapshot.manifest_id or 'missing'}; "
        f"schema={snapshot.manifest_schema_version or 'missing'}; "
        f"load={snapshot.manifest_load_state}\n"
        "Canonical files: HKP_ACTION_POLICY_STATE_v1.0.json; "
        "HKP_INTEGRITY_MANIFEST_v1.3.json\n"
        f"Background review: {'DISABLED' if snapshot.background_review_disabled else 'CHECK'}\n"
        f"Runtime probe: {runtime_state}; source={runtime.source}; "
        f"gateway_state={gateway_state}\n"
        f"Platform probe: {platform_state}\n"
        f"Voice receiver probe: {voice_state}\n"
        "Sensitive data: omitted"
    )


def render_governance_response(
    text: str | None,
    *,
    source_platform: str | None = None,
    live_platform_states: Mapping[str, bool] | None = None,
) -> str | None:
    if is_governance_status_request(text):
        return render_governance_status(
            source_platform=source_platform,
            live_platform_states=live_platform_states,
        )
    return None
