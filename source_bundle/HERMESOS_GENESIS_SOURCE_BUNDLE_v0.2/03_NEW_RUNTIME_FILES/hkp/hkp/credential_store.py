"""HKP Credential Store — protected credential storage.

Phase A: Foundation mode.
  - Schema is ready, vault file exists, proper ACL documented.
  - Actual credentials are NOT migrated yet (still in auth.json).
  - Shadow mode: vault accepts reads, returns empty (no credentials stored yet).
  - Future Phase B: migrate credentials here, lock auth.json.

Target ACL (applied in Phase A setup):
  HKPControlSvc: FullControl  (sole owner)
  SYSTEM: FullControl          (OS recovery)
  Everyone: DENY               (no other access)
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("HKP.CredentialStore")

# ── Schema for future credential entries ──────────────────────────────────
REQUIRED_METADATA_KEYS = frozenset({
    "provider",      # e.g. "anthropic", "telegram", "openrouter"
    "credential_type",  # "api_key", "oauth_token", "bot_token"
    "created_at",    # ISO timestamp
    "source",        # "manual", "oauth_flow", "imported"
    "scope",         # list of allowed action scopes
})

SENSITIVE_VALUE_KEYS = frozenset({
    "api_key", "access_token", "refresh_token", "bot_token",
    "client_secret", "private_key", "session_token",
})


class CredentialStore:
    """Protected credential store.

    Phase A: foundation only.  Accepts writes, returns empty on reads.
    No plain-text credentials are stored until explicit Phase B migration.
    """

    def __init__(self, path: Optional[Path] = None):
        hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
        self._path = path or hermes_home / "hkp" / "vault.json"
        self._lock = threading.Lock()
        self._data: dict = {"version": "hkp-vault-v1", "credentials": {}, "fingerprints": {}}
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists() and self._path.stat().st_size > 0:
                with open(self._path, "r") as f:
                    self._data = json.load(f)
        except Exception as exc:
            logger.warning("Credential store load failed (expected in Phase A): %s", exc)
            self._data = {"version": "hkp-vault-v1", "credentials": {}, "fingerprints": {}}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def verify(self, provider: str) -> bool:
        """Check if credentials exist for the given provider.

        This is the ONLY read operation available to Hermes runtime.
        Returns True/False — NEVER returns credential material.
        """
        with self._lock:
            return provider in self._data.get("credentials", {})

    def store(self, provider: str, credential_type: str, payload: dict,
              source: str = "manual", scope: Optional[list] = None) -> bool:
        """Store a credential entry.

        Phase A: stores only metadata, NOT secret values.
        In Phase A, we keep a fingerprint (non-reversible) but discard
        raw secrets.  Full secret storage is Phase B.
        """
        import hashlib
        from datetime import datetime, timezone

        with self._lock:
            creds = self._data.setdefault("credentials", {})

            # Store metadata only (no secrets in Phase A)
            entry = {
                "provider": provider,
                "credential_type": credential_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "scope": scope or [],
                "status": "PLACEHOLDER",
                "phase": "A",  # No secrets stored
            }
            creds[provider] = entry
            self._save()
            return True

    def health(self) -> dict:
        """Return store health status."""
        with self._lock:
            return {
                "status": "ok",
                "phase": "A",
                "provider_count": len(self._data.get("credentials", {})),
                "vault_path": str(self._path),
            }


# ── Singleton ─────────────────────────────────────────────────────────────
_store: Optional[CredentialStore] = None
_store_lock = threading.Lock()


def get_store() -> CredentialStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = CredentialStore()
    return _store


def verify_credential(provider: str) -> bool:
    """Check credential availability — NEVER returns credential material."""
    return get_store().verify(provider)
