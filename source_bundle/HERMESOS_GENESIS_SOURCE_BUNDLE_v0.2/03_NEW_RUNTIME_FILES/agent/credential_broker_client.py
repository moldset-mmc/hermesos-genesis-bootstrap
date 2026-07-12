#!/usr/bin/env python3
"""Hermes Credential Broker Client — IPC client for non-core processes.

Gateway, cron, tools, and employee profiles use this module to request
credential operations from the Credential Broker Service.

This module NEVER reads auth.json directly.  It communicates with the
broker over a Windows Named Pipe, and the broker authenticates callers
via OS-level pipe security descriptors (not env vars).

Usage::

    from agent.credential_broker_client import BrokerClient
    client = BrokerClient()
    result = client.verify("anthropic")  # {"has_credentials": True}
    # Note: client cannot read actual credential material
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

PIPE_NAME = r"\\.\pipe\hermes_credential_broker"
PIPE_TIMEOUT = 5  # seconds
MAX_RETRIES = 3


class BrokerUnavailable(Exception):
    """Raised when the broker is not reachable or returns an error."""
    pass


class BrokerClient:
    """Client for Hermes Credential Broker IPC.

    All methods go through the named pipe and are HKP-enforced at the
    broker side.  The broker performs OS-level caller identity verification.
    """

    def __init__(self, pipe_name: str = PIPE_NAME):
        self._pipe_name = pipe_name

    def _send_request(self, request: dict) -> dict:
        """Send a JSON request to the broker and return the response.

        Uses Windows Named Pipe client API.
        """
        import win32pipe
        import win32file
        import pywintypes

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # Try to open the named pipe
                handle = win32file.CreateFile(
                    self._pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,  # exclusive access
                    None,  # default security
                    win32file.OPEN_EXISTING,
                    0,
                    None,
                )

                # Set pipe mode
                win32pipe.SetNamedPipeHandleState(
                    handle,
                    win32pipe.PIPE_READMODE_MESSAGE,
                    None,
                    None,
                )

                # Add caller PID for extra verification
                request["caller_pid"] = os.getpid()

                # Write request
                data = json.dumps(request).encode("utf-8")
                win32file.WriteFile(handle, data)

                # Read response
                result = win32file.ReadFile(handle, 65536)
                win32file.CloseHandle(handle)

                response = json.loads(result[1].decode("utf-8"))
                return response

            except pywintypes.error as e:
                winerror = getattr(e, "winerror", 0)
                if winerror == 2:  # ERROR_FILE_NOT_FOUND — pipe doesn't exist
                    last_error = BrokerUnavailable("Broker service not running")
                elif winerror == 231:  # ERROR_PIPE_BUSY
                    last_error = BrokerUnavailable("Broker busy")
                elif winerror == 5:  # ERROR_ACCESS_DENIED
                    last_error = BrokerUnavailable("Access denied: caller not authorized")
                else:
                    last_error = BrokerUnavailable(f"Pipe error: {e}")
                time.sleep(0.5)
                continue
            except Exception as e:
                last_error = BrokerUnavailable(f"Broker error: {e}")
                time.sleep(0.5)
                continue

        raise last_error or BrokerUnavailable("Max retries exceeded")

    def verify(self, provider: str) -> bool:
        """Check if credentials exist for the given provider.

        Returns True/False.  This is the only credential operation
        available to non-core processes.
        """
        response = self._send_request({
            "action": "verify",
            "provider": provider,
        })
        if response.get("status") == "ok":
            return response.get("has_credentials", False)
        if response.get("status") == "denied":
            logger.warning("Broker denied verify: %s", response.get("reason"))
            return False
        raise BrokerUnavailable(f"Broker error: {response.get('reason', 'unknown')}")

    def health(self) -> dict:
        """Check broker health and caller authorization status."""
        try:
            response = self._send_request({"action": "health"})
            return response
        except BrokerUnavailable as e:
            return {"status": "unavailable", "error": str(e)}


# ── Legacy fallback for current code that expects direct access ────────────
# This is intentionally limited — non-core processes get only verify.
# For core processes, use the broker directly.
_broker_client = None


def _get_client() -> BrokerClient:
    global _broker_client
    if _broker_client is None:
        _broker_client = BrokerClient()
    return _broker_client


def verify_credentials(provider: str) -> bool:
    """Non-core processes: check credential availability."""
    return _get_client().verify(provider)


def broker_health() -> dict:
    """Check broker health."""
    return _get_client().health()
