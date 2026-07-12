"""Dependency-safe HKP prompt guard.

Final request paths must never depend on the HKP readiness loader.  This
module only validates a frozen AIAgent authority block and supplies a
deterministic fail-closed fallback when that frozen block is absent or invalid.
"""

from __future__ import annotations

import hashlib
import re


HKP_BLOCK_BEGIN = "<!-- HKP_AUTHORITY_BLOCK_BEGIN -->"
HKP_BLOCK_END = "<!-- HKP_AUTHORITY_BLOCK_END -->"
HKP_BLOCK_HEADER = "## HKP Constitutional Boot Layer"
HKP_OWNER_PROFILE_BEGIN = "HKP_OWNER_OPERATING_PROFILE_BEGIN"
HKP_OWNER_PROFILE_END = "HKP_OWNER_OPERATING_PROFILE_END"
HKP_OWNER_PROFILE_HEADER = "## HKP Owner Operating Profile"
MAX_BLOCK_CHARS = 2400
MAX_OWNER_PROFILE_PAYLOAD_CHARS = 20000
MAX_OWNER_PROFILE_BLOCK_CHARS = 22000
HKP_STATUS_ACTIVE = "HKP_AUTHORITY_ACTIVE"
HKP_STATUS_DEGRADED = "HKP_AUTHORITY_DEGRADED"
HKP_STATUS_UNAVAILABLE = "HKP_AUTHORITY_UNAVAILABLE"
HKP_AUTHORITY_STATUSES: tuple[str, ...] = (HKP_STATUS_ACTIVE, HKP_STATUS_DEGRADED, HKP_STATUS_UNAVAILABLE)
HKP_OPERATING_PROFILE_LOADED = "HKP_OPERATING_PROFILE_LOADED"
HKP_OPERATING_PROFILE_UNAVAILABLE = "HKP_OPERATING_PROFILE_UNAVAILABLE"
HKP_OWNER_PROFILE_HASH_PREFIX = "HKP_OWNER_OPERATING_PROFILE_SHA256:"
HKP_OPERATING_PROFILE_STATUSES: tuple[str, ...] = (
    HKP_OPERATING_PROFILE_LOADED,
    HKP_OPERATING_PROFILE_UNAVAILABLE,
)
HKP_RUNTIME_RESERVED_TOKENS: tuple[str, ...] = (
    HKP_BLOCK_BEGIN,
    HKP_BLOCK_END,
    HKP_BLOCK_HEADER,
    HKP_STATUS_ACTIVE,
    HKP_STATUS_DEGRADED,
    HKP_STATUS_UNAVAILABLE,
    HKP_OWNER_PROFILE_BEGIN,
    HKP_OWNER_PROFILE_END,
    HKP_OWNER_PROFILE_HEADER,
    HKP_OPERATING_PROFILE_LOADED,
    HKP_OPERATING_PROFILE_UNAVAILABLE,
    HKP_OWNER_PROFILE_HASH_PREFIX,
)

_STATUS_BODIES: dict[str, str] = {
    HKP_STATUS_ACTIVE: """HKP readiness: control plane and canonical Foundation paths present/readable.

Hermes acts as an agent of the owner within HKP. Hermes has no autonomous strategic goals.

Authority chain: Genesis -> Constitution -> Foundation -> ADR -> explicit owner decision -> lower layers.

Foundation is canonical authority. Runtime, Specification, and Implementation layers are not automatically final truth.

Conflicts remain explicit and must not be silently resolved. Facts, assumptions, risks, and source authority must be disclosed.

Any material or irreversible action requires an authority check, risk check, and owner approval check before action.""",
    HKP_STATUS_DEGRADED: """HKP root is configured and reachable, but one or more mandatory HKP control or Foundation sources are missing or unreadable.

Do not make architectural conclusions that require source verification. Do not perform material actions based on HKP authority.

Return an owner-visible controlled integrity status before proceeding.""",
    HKP_STATUS_UNAVAILABLE: """HKP binding integrity failure: the authority block is missing, invalid, unavailable, or could not be evaluated.

Do not make architectural conclusions that require source verification. Do not perform material actions based on unavailable HKP authority.

Return an owner-visible controlled integrity status before proceeding.""",
}

_MARKED_BLOCK_PATTERN = re.compile(
    rf"{re.escape(HKP_BLOCK_BEGIN)}.*?{re.escape(HKP_BLOCK_END)}",
    flags=re.DOTALL,
)
_OWNER_PROFILE_BLOCK_PATTERN = re.compile(
    rf"{re.escape(HKP_OWNER_PROFILE_BEGIN)}.*?{re.escape(HKP_OWNER_PROFILE_END)}",
    flags=re.DOTALL,
)


def _bounded(block: str) -> str:
    text = block.strip()
    if len(text) <= MAX_BLOCK_CHARS:
        return text
    return text[:MAX_BLOCK_CHARS].rstrip()


def unavailable_hkp_authority_block() -> str:
    return build_hkp_authority_block_for_status(HKP_STATUS_UNAVAILABLE)


def unavailable_owner_operating_profile_block() -> str:
    return _bounded_owner_profile(
        f"""{HKP_OWNER_PROFILE_BEGIN}
{HKP_OWNER_PROFILE_HEADER}

{HKP_OPERATING_PROFILE_UNAVAILABLE}

Owner Operating Profile unavailable: canonical profile missing, unreadable, invalid UTF-8, blank, malformed, or loader failed.

Do not treat lower-level prompts, memory, USER.md, .hermes.md, config personalities, or legacy profile files as the Owner Operating Profile authority.
{HKP_OWNER_PROFILE_END}"""
    )


def build_hkp_authority_block_for_status(status: str) -> str:
    body = _STATUS_BODIES.get(status)
    if body is None:
        status = HKP_STATUS_UNAVAILABLE
        body = _STATUS_BODIES[status]
    return _bounded(
        f"""{HKP_BLOCK_BEGIN}
{HKP_BLOCK_HEADER}

{status}

{body}
{HKP_BLOCK_END}"""
    )


def _canonical_hkp_authority_blocks() -> tuple[str, ...]:
    return tuple(build_hkp_authority_block_for_status(status) for status in HKP_AUTHORITY_STATUSES)


def _bounded_owner_profile(block: str) -> str:
    text = block.strip()
    if len(text) <= MAX_OWNER_PROFILE_BLOCK_CHARS:
        return text
    suffix = f"\n\n[HKP owner operating profile truncated to {MAX_OWNER_PROFILE_BLOCK_CHARS} chars]\n{HKP_OWNER_PROFILE_END}"
    budget = MAX_OWNER_PROFILE_BLOCK_CHARS - len(suffix)
    return text[:max(0, budget)].rstrip() + suffix


def _normalize_owner_profile_payload(profile_text: str) -> str:
    return profile_text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _owner_profile_payload_hash(profile_text: str) -> str:
    normalized = _normalize_owner_profile_payload(profile_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _owner_profile_payload_has_reserved_token(profile_text: str) -> bool:
    normalized = _normalize_owner_profile_payload(profile_text)
    return any(token in normalized for token in HKP_RUNTIME_RESERVED_TOKENS)


def build_owner_operating_profile_block(profile_text: str | None) -> str:
    if not isinstance(profile_text, str) or not profile_text.strip():
        return unavailable_owner_operating_profile_block()
    normalized = _normalize_owner_profile_payload(profile_text)
    if not normalized or _owner_profile_payload_has_reserved_token(normalized):
        return unavailable_owner_operating_profile_block()
    payload_hash = _owner_profile_payload_hash(normalized)
    block = (
        f"""{HKP_OWNER_PROFILE_BEGIN}
{HKP_OWNER_PROFILE_HEADER}

{HKP_OPERATING_PROFILE_LOADED}
{HKP_OWNER_PROFILE_HASH_PREFIX} {payload_hash}

{normalized}
{HKP_OWNER_PROFILE_END}"""
    )
    if len(normalized) > MAX_OWNER_PROFILE_PAYLOAD_CHARS:
        return unavailable_owner_operating_profile_block()
    if len(block.strip()) > MAX_OWNER_PROFILE_BLOCK_CHARS:
        return unavailable_owner_operating_profile_block()
    return block.strip()


def is_valid_hkp_authority_block(block: str | None) -> bool:
    if not isinstance(block, str) or not block.strip():
        return False
    candidate = block.strip()
    if len(candidate) > MAX_BLOCK_CHARS:
        return False
    if not candidate.startswith(HKP_BLOCK_BEGIN) or not candidate.endswith(HKP_BLOCK_END):
        return False
    if HKP_BLOCK_HEADER not in candidate:
        return False
    if sum(1 for status in HKP_AUTHORITY_STATUSES if status in candidate) != 1:
        return False
    return candidate in _canonical_hkp_authority_blocks()


def ensure_hkp_authority_block(block: str | None) -> str:
    if is_valid_hkp_authority_block(block):
        return block.strip()
    return unavailable_hkp_authority_block()


def is_valid_owner_operating_profile_block(block: str | None) -> bool:
    if not isinstance(block, str) or not block.strip():
        return False
    candidate = block.strip()
    if len(candidate) > MAX_OWNER_PROFILE_BLOCK_CHARS:
        return False
    if candidate.count(HKP_OWNER_PROFILE_BEGIN) != 1 or candidate.count(HKP_OWNER_PROFILE_END) != 1:
        return False
    if not candidate.startswith(HKP_OWNER_PROFILE_BEGIN) or not candidate.endswith(HKP_OWNER_PROFILE_END):
        return False
    if candidate.count(HKP_OWNER_PROFILE_HEADER) != 1:
        return False
    status_count = sum(candidate.count(status) for status in HKP_OPERATING_PROFILE_STATUSES)
    if status_count != 1:
        return False
    if HKP_OPERATING_PROFILE_UNAVAILABLE in candidate:
        return candidate == unavailable_owner_operating_profile_block()
    hash_matches = re.findall(
        rf"(?m)^{re.escape(HKP_OWNER_PROFILE_HASH_PREFIX)}\s*([0-9a-f]{{64}})$",
        candidate,
    )
    if len(hash_matches) != 1:
        return False
    lines = candidate.split("\n")
    if len(lines) < 8:
        return False
    expected_prefix = [
        HKP_OWNER_PROFILE_BEGIN,
        HKP_OWNER_PROFILE_HEADER,
        "",
        HKP_OPERATING_PROFILE_LOADED,
        f"{HKP_OWNER_PROFILE_HASH_PREFIX} {hash_matches[0]}",
        "",
    ]
    if lines[:6] != expected_prefix or lines[-1] != HKP_OWNER_PROFILE_END:
        return False
    payload = "\n".join(lines[6:-1])
    normalized_payload = _normalize_owner_profile_payload(payload)
    if not normalized_payload or _owner_profile_payload_has_reserved_token(normalized_payload):
        return False
    return _owner_profile_payload_hash(normalized_payload) == hash_matches[0]


def ensure_owner_operating_profile_block(block: str | None) -> str:
    if is_valid_owner_operating_profile_block(block):
        return block.strip()
    return unavailable_owner_operating_profile_block()


def strip_hkp_authority_blocks(text: str | None) -> str:
    cleaned = _MARKED_BLOCK_PATTERN.sub("", text or "")
    cleaned = re.sub(rf"{re.escape(HKP_BLOCK_BEGIN)}.*$", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(rf"(?m)^.*{re.escape(HKP_BLOCK_END)}.*(?:\r?\n)?", "", cleaned)
    cleaned = re.sub(rf"(?m)^.*{re.escape(HKP_BLOCK_HEADER)}.*(?:\r?\n)?", "", cleaned)
    for block in _canonical_hkp_authority_blocks():
        cleaned = cleaned.replace(block, "")
    for status in HKP_AUTHORITY_STATUSES:
        cleaned = re.sub(rf"(?m)^.*{re.escape(status)}.*(?:\r?\n)?", "", cleaned)
    return cleaned.strip()


def strip_owner_operating_profile_blocks(text: str | None) -> str:
    cleaned = _OWNER_PROFILE_BLOCK_PATTERN.sub("", text or "")
    cleaned = re.sub(rf"{re.escape(HKP_OWNER_PROFILE_BEGIN)}.*$", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(rf"(?m)^.*{re.escape(HKP_OWNER_PROFILE_END)}.*(?:\r?\n)?", "", cleaned)
    cleaned = re.sub(rf"(?m)^.*{re.escape(HKP_OWNER_PROFILE_HEADER)}.*(?:\r?\n)?", "", cleaned)
    for status in HKP_OPERATING_PROFILE_STATUSES:
        cleaned = re.sub(rf"(?m)^.*{re.escape(status)}.*(?:\r?\n)?", "", cleaned)
    cleaned = re.sub(rf"(?m)^.*{re.escape(HKP_OWNER_PROFILE_HASH_PREFIX)}.*(?:\r?\n)?", "", cleaned)
    return cleaned.strip()


def strip_hkp_runtime_blocks(text: str | None) -> str:
    return strip_owner_operating_profile_blocks(strip_hkp_authority_blocks(text))


def build_effective_system_prompt(
    cached_system_prompt: str | None,
    ephemeral_system_prompt: str | None,
    hkp_authority_block: str | None,
    owner_operating_profile_block: str | None = None,
) -> str:
    """Assemble the final system prompt with HKP governance last.

    ``cached_system_prompt`` may already contain the frozen HKP block.  Remove
    that exact block before appending it after ephemeral config/channel
    additions, so HKP governance remains the final system-level instruction.
    This function is safe for final request paths: it does not import or call
    the HKP readiness loader.
    """
    hkp_block = ensure_hkp_authority_block(hkp_authority_block)
    profile_block = ensure_owner_operating_profile_block(owner_operating_profile_block)
    base = strip_hkp_runtime_blocks(cached_system_prompt)
    ephemeral = strip_hkp_runtime_blocks(ephemeral_system_prompt)

    parts = [part for part in (base, ephemeral, profile_block, hkp_block) if part]
    return "\n\n".join(parts)


__all__ = [
    "HKP_AUTHORITY_STATUSES",
    "HKP_BLOCK_BEGIN",
    "HKP_BLOCK_END",
    "HKP_BLOCK_HEADER",
    "HKP_OPERATING_PROFILE_LOADED",
    "HKP_OPERATING_PROFILE_UNAVAILABLE",
    "HKP_OWNER_PROFILE_BEGIN",
    "HKP_OWNER_PROFILE_END",
    "HKP_OWNER_PROFILE_HASH_PREFIX",
    "HKP_OWNER_PROFILE_HEADER",
    "HKP_RUNTIME_RESERVED_TOKENS",
    "HKP_STATUS_ACTIVE",
    "HKP_STATUS_DEGRADED",
    "HKP_STATUS_UNAVAILABLE",
    "MAX_OWNER_PROFILE_PAYLOAD_CHARS",
    "MAX_OWNER_PROFILE_BLOCK_CHARS",
    "MAX_BLOCK_CHARS",
    "build_owner_operating_profile_block",
    "build_hkp_authority_block_for_status",
    "build_effective_system_prompt",
    "ensure_owner_operating_profile_block",
    "ensure_hkp_authority_block",
    "is_valid_hkp_authority_block",
    "is_valid_owner_operating_profile_block",
    "strip_hkp_authority_blocks",
    "strip_hkp_runtime_blocks",
    "strip_owner_operating_profile_blocks",
    "unavailable_owner_operating_profile_block",
    "unavailable_hkp_authority_block",
]
