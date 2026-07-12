"""HKP approval verification — Ed25519 signature verification.

Phase B Minimal: single public key, no rotation, no Credential Manager.
Public key loaded from a file path at import time.

Private key is NEVER in Hermes context. Only the public key for verification.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Public key loading ─────────────────────────────────────────────
# In staging: tests/hkp/test_ed25519_pub.key
# In production: ${HKP_APPROVAL_PUBLIC_KEY_PATH}

def _get_public_key_path() -> str:
    """Get the public key path from env var or default."""
    return os.environ.get(
        "HKP_APPROVAL_PUBLIC_KEY_PATH",
        str(Path(__file__).resolve().parent.parent / "tests" / "hkp" / "test_ed25519_pub.key"),
    )


_verifier = None  # Lazily loaded


def _load_verifier():
    """Load the Ed25519 public key and return a verifier callable."""
    global _verifier
    if _verifier is not None:
        return _verifier

    path = Path(_get_public_key_path())
    if not path.exists():
        logger.warning("HKP approval public key not found at %s — all verifications will fail closed", path)
        _verifier = None
        return None

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization

        key_bytes = path.read_bytes()
        pub_key = Ed25519PublicKey.from_public_bytes(key_bytes)
        _verifier = pub_key
        logger.info("HKP approval public key loaded from %s", path)
        return _verifier
    except Exception as exc:
        logger.error("Failed to load Ed25519 public key from %s: %s", path, exc)
        _verifier = None
        return None


def verify_approval(token: dict[str, Any] | None) -> dict[str, Any]:
    """Verify an approval token.

    Returns:
        {"valid": True, ...} on success
        {"valid": False, "reason": "..."} on failure
    """
    if token is None:
        return {"valid": False, "reason": "no_token"}

    # Required fields
    required = {"approval_id", "scope", "target", "expires", "issued_by", "signature"}
    missing = required - set(token.keys())
    if missing:
        return {"valid": False, "reason": f"missing_fields: {missing}"}

    # Expiry check
    expires_str = token.get("expires", "")
    try:
        expires_ts = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        if expires_ts.tzinfo is None:
            expires_ts = expires_ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return {"valid": False, "reason": "invalid_expires_format"}

    if datetime.now(timezone.utc) >= expires_ts:
        return {"valid": False, "reason": "expired"}

    # Load verifier
    verifier = _load_verifier()
    if verifier is None:
        return {"valid": False, "reason": "public_key_not_available"}

    # Rebuild signed message
    # The signed payload is: approval_id|scope|target|expires|issued_by
    signed_payload = (
        f"{token['approval_id']}|{token['scope']}|{token['target']}|"
        f"{token['expires']}|{token['issued_by']}"
    ).encode("utf-8")

    signature_b64 = token.get("signature", "")
    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        return {"valid": False, "reason": "invalid_signature_encoding"}

    try:
        verifier.verify(signature, signed_payload)
        return {
            "valid": True,
            "approval_id": token["approval_id"],
            "scope": token["scope"],
            "target": token["target"],
            "issued_by": token["issued_by"],
        }
    except Exception:
        return {"valid": False, "reason": "bad_signature"}


def sign_token(
    payload: dict[str, Any],
    private_key_b64: str,
) -> dict[str, Any]:
    """Sign an approval token with the given Ed25519 private key (base64).

    This is ONLY for test/signing tooling — never called inside Hermes.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv_bytes = base64.b64decode(private_key_b64)
    priv_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)

    signed_payload = (
        f"{payload['approval_id']}|{payload['scope']}|{payload['target']}|"
        f"{payload['expires']}|{payload['issued_by']}"
    ).encode("utf-8")

    signature = priv_key.sign(signed_payload)
    token = dict(payload)
    token["signature"] = base64.b64encode(signature).decode()
    return token
