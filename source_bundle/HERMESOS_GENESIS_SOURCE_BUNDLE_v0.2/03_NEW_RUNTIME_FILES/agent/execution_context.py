"""HKP Execution Context вЂ” runtime-assigned, not prompt-layer.

Uses contextvars.ContextVar for asyncio-safe, thread-safe context propagation.
Default: UNKNOWN вЂ” all write tools blocked, only minimal diagnostics allowed.
Never fail-opens to FOREGROUND.
"""

from __future__ import annotations

from contextvars import ContextVar
from enum import Enum


class ExecutionContext(str, Enum):
    """Immutable execution context assigned by runtime, never by LLM.

    UNKNOWN is the safe default вЂ” all write operations blocked,
    only diagnostic reads (file_read, search_files, web_search) allowed.
    """

    UNKNOWN = "unknown"
    FOREGROUND = "foreground"
    FOREGROUND_OWNER = "foreground_owner"
    BACKGROUND_REVIEW_READ_ONLY = "bg_review_ro"
    CRON_NO_AGENT = "cron_no_agent"
    CRON_AGENT = "cron_agent"
    EMPLOYEE_PROFILE = "employee"
    SUBAGENT = "subagent"


# ContextVar вЂ” automatically copied to each asyncio.Task.
# Not accessible to LLM, not spoofable from tool arguments.
_execution_context: ContextVar[ExecutionContext] = ContextVar(
    "hkp_execution_context",
    default=ExecutionContext.UNKNOWN,
)


def set_execution_context(ctx: ExecutionContext) -> None:
    """Set the current execution context. Called by runtime entry points only."""
    _execution_context.set(ctx)


def get_execution_context() -> ExecutionContext:
    """Get the current execution context. Never returns None."""
    return _execution_context.get()


def clear_execution_context() -> None:
    """Reset to UNKNOWN. Called in finally blocks."""
    _execution_context.set(ExecutionContext.UNKNOWN)

