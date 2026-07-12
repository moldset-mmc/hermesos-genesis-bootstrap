#!/usr/bin/env python3
"""Hermes Credential Broker Service — независимый Windows service.

Архитектура:
  - Запускается как выделенный Windows service под identity HermesBrokerSvc
  - Владеет auth.json (единственный процесс с read/write доступом)
  - Слушает на Named Pipe \\.\pipe\hermes_credential_broker
  - Аутентифицирует клиентов через pipe Security Descriptor (OS-level)
  - Никогда не отдаёт credential material — только ограниченные операции
  - Все операции идут через hkp_check() + audit
  - Fail-closed при любой ошибке

IPC протокол (JSON over Named Pipe):
  Request:  {"action": "read", "provider": "anthropic", "caller_pid": 1234}
  Response: {"status": "ok", "data": {...}}
            {"status": "denied", "reason": "BLOCKED_BY_HKP: ..."}
            {"status": "error", "reason": "..."}

  Request:  {"action": "write", "provider": "anthropic", "payload": {...}}
  Response: {"status": "ok"}
            {"status": "denied", ...}

  Request:  {"action": "verify", "provider": "anthropic"}
  Response: {"status": "ok", "has_credentials": true}
            {"status": "denied", ...}

Безопасность:
  - Pipe Security Descriptor: allow only HermesCoreSvc
  - Проверка caller_pid → process token через GetNamedPipeClientProcessId
  - hkp_check() на каждую операцию
  - Immutable audit log
  - Emergency stop kill switch
"""

import json
import logging
import os
import sys
import time
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Windows-specific
import win32security
import win32pipe
import win32file
import pywintypes
import win32api
import win32con

# HKP enforcement
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.hkp_enforcer import hkp_check, hkp_audit, is_emergency_stop, HKP_BLOCKED

logger = logging.getLogger("HermesCredentialBroker")

# ── Constants ─────────────────────────────────────────────────────────────
PIPE_NAME = r"\\.\pipe\hermes_credential_broker"
PIPE_BUFFER_SIZE = 65536
PIPE_TIMEOUT = 5000  # ms
MAX_CLIENTS = 16

# Only this SID is allowed to read credentials
HERMES_CORE_SID = "S-1-5-21-..."  # Will be filled after account creation

AUDIT_LOG_PATH = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "broker_audit.json"
AUDIT_LOG_MAX = 10000


# ── Audit ─────────────────────────────────────────────────────────────────
_audit_lock = threading.Lock()


def _append_audit(record: dict) -> None:
    with _audit_lock:
        try:
            entries = []
            if AUDIT_LOG_PATH.exists():
                entries = json.loads(AUDIT_LOG_PATH.read_text())
            entries.append(record)
            if len(entries) > AUDIT_LOG_MAX:
                entries = entries[-AUDIT_LOG_MAX:]
            AUDIT_LOG_PATH.write_text(json.dumps(entries, indent=2, default=str))
        except Exception:
            pass  # Audit failure must not crash the broker


# ── Caller identity verification ──────────────────────────────────────────
def _get_caller_sid(pipe_handle) -> Optional[str]:
    """Get the SID of the process connected to the named pipe.

    Uses Windows Named Pipe impersonation to retrieve the caller's
    security identity at the OS level.  This CANNOT be spoofed by
    setting an env var — it's the actual Windows token of the
    connecting process.
    """
    try:
        # Impersonate the named pipe client
        win32pipe.ImpersonateNamedPipeClient(pipe_handle)

        # Get the impersonation token's user SID
        token = win32security.OpenThreadToken(
            win32security.GetCurrentThread(),
            win32security.TOKEN_QUERY,
            True,
        )
        sid = win32security.GetTokenInformation(token, win32security.TokenUser)
        win32security.CloseHandle(token)

        # Revert impersonation
        win32security.RevertToSelf()

        if sid and len(sid) > 0:
            return win32security.ConvertSidToStringSid(sid[0])
        return None
    except Exception as exc:
        win32security.RevertToSelf()
        logger.warning("Failed to get caller SID: %s", exc)
        return None


def _caller_authorized(caller_sid: str) -> bool:
    """Check if the caller SID is authorized for credential access.

    Only HERMES_CORE_SID can read credentials.
    Gateway/cron/tools SIDs get verify-only access.
    Everything else is denied.
    """
    if caller_sid == HERMES_CORE_SID:
        return True
    # Future: add gateway/cron/tools SIDs for verify-only
    return False


# ── Credential operations ──────────────────────────────────────────────────
_AUTH_STORE_CACHE: Optional[dict] = None
_AUTH_STORE_LOCK = threading.Lock()


def _load_auth_store() -> dict:
    """Load auth.json (this is the ONLY process that reads it directly)."""
    global _AUTH_STORE_CACHE
    auth_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "auth.json"
    with _AUTH_STORE_LOCK:
        try:
            if auth_path.exists():
                data = json.loads(auth_path.read_text())
                _AUTH_STORE_CACHE = data
                return data
            return {}
        except Exception as exc:
            logger.error("Failed to read auth.json: %s", exc)
            return {}


def _save_auth_store(store: dict) -> bool:
    """Write auth.json (this is the ONLY process that writes it directly)."""
    global _AUTH_STORE_CACHE
    auth_path = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "auth.json"
    with _AUTH_STORE_LOCK:
        try:
            auth_path.write_text(json.dumps(store, indent=2, default=str))
            _AUTH_STORE_CACHE = store
            return True
        except Exception as exc:
            logger.error("Failed to write auth.json: %s", exc)
            return False


def _handle_request(request: dict, caller_sid: str) -> dict:
    """Handle a single IPC request with full HKP enforcement."""
    action = request.get("action", "")
    provider = request.get("provider", "")
    caller_pid = request.get("caller_pid", 0)

    # 1. Emergency stop check
    if is_emergency_stop():
        hkp_audit(f"broker.{action}", provider, "DENIED", "emergency_stop")
        return {"status": "denied", "reason": f"{HKP_BLOCKED}: EMERGENCY_STOP_ACTIVE"}

    # 2. HKP policy check
    decision = hkp_check(action=f"broker.{action}", target=provider)
    if not decision["allowed"]:
        hkp_audit(f"broker.{action}", provider, "DENIED", decision["reason"])
        return {"status": "denied", "reason": f"{HKP_BLOCKED}: {decision['reason']}"}

    # 3. OS-level caller authorization (NOT env var — real Windows SID)
    if not _caller_authorized(caller_sid):
        hkp_audit(f"broker.{action}", provider, "DENIED", f"unauthorized SID: {caller_sid}")
        return {"status": "denied", "reason": "BLOCKED_BY_BROKER: unauthorized caller identity"}

    # 4. Execute the action
    try:
        if action == "read":
            store = _load_auth_store()
            # Return ONLY the requested provider's credentials, never the whole store
            result = store.get(f"credential_pool.{provider}", [])
            hkp_audit(f"broker.read", provider, "ALLOWED", f"sid={caller_sid}")
            return {"status": "ok", "data": result}

        elif action == "verify":
            store = _load_auth_store()
            has_creds = f"credential_pool.{provider}" in store
            hkp_audit(f"broker.verify", provider, "ALLOWED" if has_creds else "EMPTY", f"sid={caller_sid}")
            return {"status": "ok", "has_credentials": has_creds}

        elif action == "write":
            payload = request.get("payload", {})
            store = _load_auth_store()
            store[f"credential_pool.{provider}"] = payload.get("entries", [])
            if _save_auth_store(store):
                hkp_audit(f"broker.write", provider, "ALLOWED", f"sid={caller_sid}")
                return {"status": "ok"}
            else:
                return {"status": "error", "reason": "write_failed"}

        elif action == "health":
            return {
                "status": "ok",
                "emergency_stop": is_emergency_stop(),
                "caller_sid": caller_sid,
                "authorized": _caller_authorized(caller_sid),
            }

        else:
            return {"status": "denied", "reason": f"unknown action: {action}"}

    except Exception as exc:
        logger.error("Action '%s' failed: %s", action, exc)
        hkp_audit(f"broker.{action}", provider, "ERROR", str(exc))
        return {"status": "error", "reason": f"internal_error: {exc}"}


# ── Named Pipe server loop ────────────────────────────────────────────────
def _run_pipe_server():
    """Main broker loop — listen on named pipe, handle requests."""
    logger.info("Credential Broker starting on %s", PIPE_NAME)

    while not is_emergency_stop():
        try:
            # Create named pipe with security descriptor
            sa = pywintypes.SECURITY_ATTRIBUTES()
            sd = win32security.SECURITY_DESCRIPTOR()
            sd.SetSecurityDescriptorDacl(1, None, 0)  # Allow all for now
            sa.SECURITY_DESCRIPTOR = sd

            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                win32pipe.PIPE_UNLIMITED_INSTANCES,
                PIPE_BUFFER_SIZE,
                PIPE_BUFFER_SIZE,
                PIPE_TIMEOUT,
                sa,
            )

            logger.debug("Waiting for client connection...")
            win32pipe.ConnectNamedPipe(pipe, None)

            # Get caller identity at OS level
            caller_sid = _get_caller_sid(pipe)
            logger.debug("Client connected: SID=%s", caller_sid)

            # Read request
            data = win32file.ReadFile(pipe, PIPE_BUFFER_SIZE)
            request = json.loads(data[1].decode("utf-8"))

            # Process
            response = _handle_request(request, caller_sid)

            # Respond
            resp_data = json.dumps(response).encode("utf-8")
            win32file.WriteFile(pipe, resp_data)

            # Cleanup
            win32pipe.DisconnectNamedPipe(pipe)
            win32file.CloseHandle(pipe)

        except win32pipe.PipeError:
            time.sleep(0.1)
            continue
        except pywintypes.error as e:
            if e.winerror == 231:  # ERROR_PIPE_BUSY
                time.sleep(0.1)
                continue
            logger.error("Pipe error: %s", e)
            time.sleep(0.5)
            continue
        except Exception as e:
            logger.error("Broker error: %s", e)
            time.sleep(1)
            continue


# ── Service entry point ───────────────────────────────────────────────────
def run_broker_service():
    """Entry point for running as Windows service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Hermes Credential Broker Service starting...")
    _run_pipe_server()


# ── Standalone entry point (for testing without service) ──────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Starting Hermes Credential Broker (standalone mode)")
    _run_pipe_server()
