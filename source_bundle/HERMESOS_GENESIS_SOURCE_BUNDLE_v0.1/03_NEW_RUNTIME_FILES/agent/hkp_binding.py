"""HKP authority binding for Hermes system prompts.

This module deliberately reads only a small set of control-document paths.
It never loads HKP document contents into the prompt.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from agent.hkp_prompt_guard import (
    HKP_STATUS_ACTIVE,
    HKP_STATUS_DEGRADED,
    HKP_STATUS_UNAVAILABLE,
    build_hkp_authority_block_for_status,
)


CONTROL_DOCUMENTS: tuple[str, ...] = (
    "README.md",
    "HKP_INDEX.md",
    "DOCUMENT_REGISTRY.md",
    "HKP_DEPENDENCY_MAP.md",
    "HKP_AUDIT_REPORT.md",
)

OWNER_OPERATING_PROFILE_RELATIVE_PATH = (
    "Operating Layer/HERMES_OWNER_OPERATING_PROFILE_v1.0.md"
)

FOUNDATION_SOURCE_PATHS: tuple[str, ...] = (
    "01_Hermes_OS_Architectural_Level_1/GENESIS_000.txt",
    "HERMES_OS_CORE_FOUNDATION_INDEX_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_GLOSSARY_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_CONSTITUTION_v1.0.docx",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_OPERATING_MODEL_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_REGISTRY_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_CORE_BOOTSTRAP_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_ARCHITECTURE_DECISIONS_v1.0.txt",
    "01_Hermes_OS_Architectural_Level_1/HERMES_FOUNDATION_RELEASE_1.0_CANONICAL_RESOLUTION.docx",
)

def _is_readable_file(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        with path.open("rb"):
            return True
    except OSError:
        return False


def _control_documents_available(root: Path, names: Iterable[str] = CONTROL_DOCUMENTS) -> bool:
    return all(_is_readable_file(root / name) for name in names)


def _foundation_sources_available(root: Path, paths: Iterable[str] = FOUNDATION_SOURCE_PATHS) -> bool:
    return all(_is_readable_file(root / rel_path) for rel_path in paths)


def build_hkp_authority_block() -> str:
    """Build the HKP governance block for the system prompt.

    The only configuration source is ``HKP_AUTHORITY_ROOT``.  When it is unset,
    invalid, or unreadable, the function returns a deterministic unavailable
    block.  When the root is reachable but required sources are incomplete, it
    returns a deterministic degraded-mode block.
    """
    raw_root = os.environ.get("HKP_AUTHORITY_ROOT", "").strip()
    if not raw_root:
        return build_hkp_authority_block_for_status(HKP_STATUS_UNAVAILABLE)

    try:
        root = Path(raw_root).expanduser()
    except (OSError, RuntimeError, ValueError):
        return build_hkp_authority_block_for_status(HKP_STATUS_UNAVAILABLE)

    try:
        if not root.is_dir():
            return build_hkp_authority_block_for_status(HKP_STATUS_UNAVAILABLE)
    except OSError:
        return build_hkp_authority_block_for_status(HKP_STATUS_UNAVAILABLE)

    if not _control_documents_available(root):
        return build_hkp_authority_block_for_status(HKP_STATUS_DEGRADED)

    if not _foundation_sources_available(root):
        return build_hkp_authority_block_for_status(HKP_STATUS_DEGRADED)

    return build_hkp_authority_block_for_status(HKP_STATUS_ACTIVE)


def load_owner_operating_profile_text() -> str:
    """Load the canonical Owner Operating Profile text.

    This uses only ``HKP_AUTHORITY_ROOT`` plus the exact canonical relative
    path.  It deliberately does not search for similarly named files and does
    not fall back to legacy profile/personality/memory sources.
    """
    raw_root = os.environ.get("HKP_AUTHORITY_ROOT", "").strip()
    if not raw_root:
        raise FileNotFoundError("HKP_AUTHORITY_ROOT is not set")

    root = Path(raw_root).expanduser()
    profile_path = root / OWNER_OPERATING_PROFILE_RELATIVE_PATH
    return profile_path.read_text(encoding="utf-8")


__all__ = [
    "CONTROL_DOCUMENTS",
    "FOUNDATION_SOURCE_PATHS",
    "OWNER_OPERATING_PROFILE_RELATIVE_PATH",
    "build_hkp_authority_block",
    "load_owner_operating_profile_text",
]
