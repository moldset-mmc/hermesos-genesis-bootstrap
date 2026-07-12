"""HKP preflight dispatcher — deny-by-default tool-layer enforcement.

Evaluates every tool call against execution context and returns one of:
  ALLOWED | BLOCKED | PROPOSE | DENY

No explicit ALLOW rule = BLOCKED (deny-by-default).
UNKNOWN context: only minimal diagnostics (file_read, search_files, web_search).
"""

from __future__ import annotations

import logging
import os

from agent.execution_context import ExecutionContext, get_execution_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Read-only tools — available in any known non-UNKNOWN context.
# memory_read, web_search, web_extract removed — they have context-specific
# handlers below (memory_read is scoped by target; web tools are outbound).
# ---------------------------------------------------------------------------
READ_ONLY_TOOLS = frozenset({
    "skill_view",
    "skills_list",
    "honcho_profile",
    "honcho_search",
    "honcho_context",
    "session_search",
})

# ---------------------------------------------------------------------------
# Diagnostic tools — the only tools available in UNKNOWN context
# ---------------------------------------------------------------------------
DIAGNOSTIC_TOOLS = frozenset({
    "read_file",
    "search_files",
})

# ---------------------------------------------------------------------------
# Write tools — require context check
# ---------------------------------------------------------------------------
WRITE_TOOLS = frozenset({
    "memory_write",
    "skill_manage",
    "write_file",
    "patch",
    "delete",
    "cronjob",
    "terminal",
})

# ---------------------------------------------------------------------------
# Context-sensitive tool scopes for file_read
# ---------------------------------------------------------------------------
SENSITIVE_PATTERNS = frozenset({
    ".env",
    ".hermes.md",
    "config.yaml",
    "credentials",
    "secrets",
    "hkp_approval_key",
    "approval_registry",
    "/HKP/",
})

# ---------------------------------------------------------------------------
# Evidence path for append-only writes
# ---------------------------------------------------------------------------
EVIDENCE_BASE = os.environ.get("HKP_EVIDENCE_BASE", os.path.join(os.environ.get("HKP_AUTHORITY_ROOT", ""), "Runtime Layer/audit/policy_gate/reports"))


def is_sensitive_path(path: str) -> bool:
    """Check if a file path matches a sensitive pattern.

    Excludes the evidence/reports path from HKP sensitivity check.
    """
    lower = path.lower().replace("\\", "/")
    # Evidence path is explicitly allowed
    evidence_lower = EVIDENCE_BASE.lower().replace("\\", "/")
    if lower.startswith(evidence_lower):
        return False
    for pat in SENSITIVE_PATTERNS:
        if pat.lower() in lower:
            return True
    return False


def resolve_safe_path(path: str) -> str | None:
    """Resolve and validate evidence path. Returns None if unsafe."""
    import os
    try:
        resolved = os.path.realpath(path)
    except Exception:
        return None
    if not resolved.startswith(os.path.realpath(EVIDENCE_BASE) + os.sep):
        return None
    if os.path.exists(resolved):
        return None  # create-only, no overwrite
    return resolved


# ---------------------------------------------------------------------------
# Preflight result
# ---------------------------------------------------------------------------
class PreflightResult:
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    PROPOSE = "PROPOSE"
    DENY = "DENY"
    DRY_RUN_ALLOW = "DRY_RUN_ALLOW"


def _is_dry_run() -> bool:
    """Check if preflight is in dry-run (audit-only) mode.

    In dry-run mode, all tools are allowed but decisions are logged.
    Controlled by environment variable HKP_PREFLIGHT_DRY_RUN=true/false.
    Default: False (enforcement mode).
    """
    val = os.environ.get("HKP_PREFLIGHT_DRY_RUN", "").strip().lower()
    return val in ("true", "1", "yes")


def preflight_file_read(ctx: ExecutionContext, path: str) -> str:
    """Scope-limited file_read preflight."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.ALLOWED  # diagnostic only
    if is_sensitive_path(path):
        if ctx == ExecutionContext.FOREGROUND:
            return PreflightResult.ALLOWED
        if ctx == ExecutionContext.FOREGROUND_OWNER:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED
    return PreflightResult.ALLOWED


def preflight_file_write(ctx: ExecutionContext, path: str) -> str:
    """Evidence-append-only or blocked."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx == ExecutionContext.BACKGROUND_REVIEW_READ_ONLY:
        safe = resolve_safe_path(path)
        if safe is not None:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED
    if ctx in (ExecutionContext.CRON_NO_AGENT, ExecutionContext.CRON_AGENT):
        safe = resolve_safe_path(path)
        if safe is not None:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED
    if is_sensitive_path(path):
        return PreflightResult.PROPOSE
    return PreflightResult.ALLOWED


def preflight_patch(ctx: ExecutionContext, path: str) -> str:
    """Patch is a write operation — blocked in background/cron."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx in (ExecutionContext.BACKGROUND_REVIEW_READ_ONLY,
               ExecutionContext.CRON_NO_AGENT,
               ExecutionContext.CRON_AGENT):
        return PreflightResult.BLOCKED
    if is_sensitive_path(path):
        return PreflightResult.PROPOSE
    return PreflightResult.ALLOWED


def preflight_terminal(ctx: ExecutionContext, command: str) -> str:
    """Terminal — blocked in background, side-effect check for cron."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx == ExecutionContext.BACKGROUND_REVIEW_READ_ONLY:
        return PreflightResult.BLOCKED
    return PreflightResult.ALLOWED


def preflight_cron(ctx: ExecutionContext, action: str) -> str:
    """Cron management — PROPOSE in foreground, BLOCKED elsewhere."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx in (ExecutionContext.FOREGROUND,
               ExecutionContext.FOREGROUND_OWNER):
        return PreflightResult.PROPOSE
    return PreflightResult.BLOCKED


def preflight_memory_read(ctx: ExecutionContext, target: str) -> str:
    """Memory read — scoped by target and context.

    BACKGROUND_REVIEW_READ_ONLY:
      session, project         → ALLOWED (non-sensitive)
      canonical                → ALLOWED only if sanitized / no secrets
      user                     → BLOCKED (foreground Owner only)
      governance               → BLOCKED (foreground Owner only)

    UNKNOWN context:
      → BLOCKED unless explicitly diagnostic and non-sensitive.
    """
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx == ExecutionContext.BACKGROUND_REVIEW_READ_ONLY:
        if target in ("user", "governance"):
            return PreflightResult.BLOCKED
        return PreflightResult.ALLOWED
    # All other contexts (FOREGROUND, etc.)
    return PreflightResult.ALLOWED


def preflight_memory_write(ctx: ExecutionContext, target: str) -> str:
    """Memory write — BLOCKED in background/cron, PROPOSE for canonical."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx in (ExecutionContext.BACKGROUND_REVIEW_READ_ONLY,
               ExecutionContext.CRON_NO_AGENT,
               ExecutionContext.CRON_AGENT):
        return PreflightResult.BLOCKED
    if target == "governance":
        return PreflightResult.DENY
    if target in ("canonical",):
        return PreflightResult.PROPOSE
    return PreflightResult.ALLOWED


def preflight_skill_manage(ctx: ExecutionContext, action: str, skill_class: str) -> str:
    """Skill management with class/context checks."""
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx in (ExecutionContext.BACKGROUND_REVIEW_READ_ONLY,
               ExecutionContext.CRON_NO_AGENT,
               ExecutionContext.CRON_AGENT,
               ExecutionContext.EMPLOYEE_PROFILE):
        return PreflightResult.BLOCKED

    # Governance skills — always DENY
    if skill_class == "governance":
        return PreflightResult.DENY

    # Approved/canonical write — PROPOSE
    if skill_class in ("approved", "canonical") and action in ("create", "edit", "delete"):
        return PreflightResult.PROPOSE

    # Promotion — PROPOSE
    if action == "promote":
        return PreflightResult.PROPOSE

    # Autoload — PROPOSE
    if action == "autoload":
        return PreflightResult.PROPOSE

    # Operational/draft in foreground (incl. authenticated Owner) — ALLOWED.
    if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER) and skill_class in ("operational", "draft"):
        return PreflightResult.ALLOWED

    return PreflightResult.BLOCKED


OUTBOUND_TOOLS = frozenset({
    "web_search",
    "web_extract",
})


def preflight_outbound(ctx: ExecutionContext, method_or_tool: str) -> str:
    """Outbound HTTP or web tool — blocked in background/cron/UNKNOWN.

    BACKGROUND_REVIEW_READ_ONLY: ALL web/network outbound BLOCKED.
    GET/POST/PUT/DELETE methods → BLOCKED.
    web_search, web_extract → BLOCKED.
    """
    if ctx == ExecutionContext.UNKNOWN:
        return PreflightResult.BLOCKED
    if ctx == ExecutionContext.BACKGROUND_REVIEW_READ_ONLY:
        return PreflightResult.BLOCKED
    if method_or_tool.upper() in ("POST", "PUT", "DELETE", "PATCH", "GET"):
        return PreflightResult.PROPOSE
    return PreflightResult.ALLOWED


# ---------------------------------------------------------------------------
# Main dispatcher — deny-by-default
# ---------------------------------------------------------------------------
def preflight(tool_name: str, tool_args: dict | None = None) -> str:
    """Evaluate tool call against current execution context.

    Returns one of: ALLOWED, BLOCKED, PROPOSE, DENY
    Deny-by-default — no explicit ALLOW rule = BLOCKED.
    """
    ctx = get_execution_context()
    args = tool_args or {}

    # UNKNOWN context: only diagnostics
    if ctx == ExecutionContext.UNKNOWN:
        if tool_name in DIAGNOSTIC_TOOLS:
            return PreflightResult.ALLOWED
        if tool_name == "memory_read":
            return PreflightResult.BLOCKED
        if tool_name in OUTBOUND_TOOLS:
            return PreflightResult.BLOCKED
        if tool_name in READ_ONLY_TOOLS:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # SUBAGENT context — CHECKED FIRST, before any tool-name handlers,
    # so subagent never inherits FOREGROUND_OWNER rights via a generic
    # handler that only checks tool_name (terminal, write_file, etc.).
    if ctx == ExecutionContext.SUBAGENT:
            if tool_name in READ_ONLY_TOOLS or tool_name in DIAGNOSTIC_TOOLS:
                return PreflightResult.ALLOWED
            if tool_name == "memory":
                target = args.get("target", "session")
                return preflight_memory_read(ctx, target)
            if tool_name in ("memory_read",):
                target = args.get("target", "session")
                return preflight_memory_read(ctx, target)
            return PreflightResult.BLOCKED

    # Route to context-specific handlers
    # Memory tool — map to memory_read/memory_write by action
    if tool_name == "memory":
        action = args.get("action")
        if action in ("add", "replace", "remove"):
            target = args.get("target", "memory")
            return preflight_memory_write(ctx, target)
        # No action or read/search/list action — treat as read
        target = args.get("target", "session")
        return preflight_memory_read(ctx, target)

    if tool_name == "memory_read":
        target = args.get("target", "session")
        return preflight_memory_read(ctx, target)

    if tool_name in OUTBOUND_TOOLS:
        return preflight_outbound(ctx, tool_name)

    if tool_name in READ_ONLY_TOOLS:
        return PreflightResult.ALLOWED

    if tool_name in DIAGNOSTIC_TOOLS:
        return PreflightResult.ALLOWED

    if tool_name == "memory_write":
        target = args.get("target", "session")
        return preflight_memory_write(ctx, target)

    if tool_name == "skill_manage":
        action = args.get("action", "")
        skill_class = args.get("skill_class", "operational")
        return preflight_skill_manage(ctx, action, skill_class)

    if tool_name in ("write_file",):
        path = args.get("path", "")
        return preflight_file_write(ctx, path)

    if tool_name in ("patch",):
        path = args.get("path", "")
        return preflight_patch(ctx, path)

    if tool_name in ("delete",):
        return PreflightResult.PROPOSE

    if tool_name == "terminal":
        command = args.get("command", "")
        return preflight_terminal(ctx, command)

    if tool_name == "cronjob":
        action = args.get("action", "")
        return preflight_cron(ctx, action)

    # Todo/task tracking — essential for long tasks and iteration-limit recovery
    if tool_name == "todo":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Delegate_task — parent FOREGROUND_OWNER spawns subagents (SUBAGENT context)
    if tool_name == "delegate_task":
        if ctx == ExecutionContext.FOREGROUND_OWNER:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Execute_code — safe in foreground, needed for development/automation
    if tool_name == "execute_code":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Clarify — safe in foreground (asks user)
    if tool_name == "clarify":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Process management — background processes in foreground
    if tool_name == "process":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Honcho reasoning — synthesized answers (read-only in foreground)
    if tool_name == "honcho_reasoning":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Honcho conclude — write facts with classification (foreground owner only)
    if tool_name == "honcho_conclude":
        if ctx == ExecutionContext.FOREGROUND_OWNER:
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Image generation — blocked in background/cron, allowed in foreground
    if tool_name == "image_generate":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Text-to-speech — allowed in foreground
    if tool_name == "text_to_speech":
        if ctx in (ExecutionContext.FOREGROUND, ExecutionContext.FOREGROUND_OWNER):
            return PreflightResult.ALLOWED
        return PreflightResult.BLOCKED

    # Deny-by-default: no explicit ALLOW rule
    return PreflightResult.BLOCKED