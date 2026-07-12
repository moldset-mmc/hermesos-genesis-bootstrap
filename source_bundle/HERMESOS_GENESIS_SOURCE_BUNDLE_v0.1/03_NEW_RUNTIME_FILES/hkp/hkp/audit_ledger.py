"""HKP Audit Ledger — immutable append-only event log.

Phase A: file-based JSON ledger. Production: SQLite or dedicated audit store.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class AuditLedger:
    """Thread-safe, append-only audit ledger.

    Every operation record is immutable once written.  Ledger has a
    configurable max size; oldest entries are pruned when exceeded.
    """

    def __init__(self, path: Optional[Path] = None, max_entries: int = 50000):
        hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        self._path = path or hermes_home / "hkp" / "audit_ledger.json"
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists() and self._path.stat().st_size > 0:
                with open(self._path, "r") as f:
                    self._entries = json.load(f)
        except Exception:
            self._entries = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        entries = self._entries[-self._max_entries:]
        with open(self._path, "w") as f:
            json.dump(entries, f, indent=2, default=str)

    def append(self, entry: dict) -> str:
        """Append an audit entry. Returns the audit_id."""
        audit_id = f"aud_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        record = {
            "audit_id": audit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        with self._lock:
            self._entries.append(record)
            self._save()
        return audit_id

    def query(self, limit: int = 100, action_filter: Optional[str] = None,
              since: Optional[str] = None) -> list[dict]:
        """Query audit entries. Returns most recent first."""
        with self._lock:
            results = list(reversed(self._entries))
        if action_filter:
            results = [e for e in results if e.get("action_type", "") == action_filter]
        if since:
            results = [e for e in results if e.get("timestamp", "") >= since]
        return results[:limit]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries = []
            self._save()


# ── Singleton ─────────────────────────────────────────────────────────────
_ledger: Optional[AuditLedger] = None
_ledger_lock = threading.Lock()


def get_ledger() -> AuditLedger:
    global _ledger
    if _ledger is None:
        with _ledger_lock:
            if _ledger is None:
                _ledger = AuditLedger()
    return _ledger


def audit_event(action_type: str, target: str, result: str, reason: str = "",
                request_id: str = "", caller_info: Optional[dict] = None,
                policy_class: str = "") -> str:
    """Convenience: append an audit event. Returns audit_id."""
    ledger = get_ledger()
    entry = {
        "action_type": action_type,
        "target": target,
        "result": result,
        "reason": reason,
        "request_id": request_id,
        "caller": caller_info or {},
        "policy_class": policy_class,
    }
    return ledger.append(entry)
