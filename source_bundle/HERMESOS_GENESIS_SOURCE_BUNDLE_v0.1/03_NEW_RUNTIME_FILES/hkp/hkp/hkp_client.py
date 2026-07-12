"""HKP Control Plane Client — Hermes runtime IPC adapter.

Hermes runtime uses this client to send typed action requests to the
HKP Control Plane Broker.  In Phase A (shadow mode), all requests
are audited but the runtime continues to work through direct paths.

Phase B+: runtime routes ALL sensitive operations through this client,
and the Broker is the only process with external API access.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

BROKER_HOST = os.environ.get("HKP_BROKER_HOST", "127.0.0.1")
BROKER_PORT = int(os.environ.get("HKP_BROKER_PORT", "9877"))
BROKER_URL = f"http://{BROKER_HOST}:{BROKER_PORT}"
REQUEST_TIMEOUT = 10  # seconds


class BrokerConnectionError(Exception):
    """Raised when the Control Plane broker is unreachable."""
    pass


class BrokerDenied(Exception):
    """Raised when the Control Plane broker denies an action."""
    def __init__(self, reason: str, policy_class: str = ""):
        self.reason = reason
        self.policy_class = policy_class
        super().__init__(f"[{policy_class}] {reason}")


class HKPClient:
    """Client for HKP Control Plane typed action requests.

    Thread-safe (no mutable shared state in methods).
    """

    def __init__(self, broker_url: str = BROKER_URL, timeout: int = REQUEST_TIMEOUT):
        self._broker_url = broker_url.rstrip("/")
        self._timeout = timeout

    def _request_id(self) -> str:
        return str(uuid.uuid4())

    def _call_broker(self, endpoint: str, body: dict) -> dict:
        """Send a request to the broker. Returns parsed response."""
        url = f"{self._broker_url}{endpoint}"
        data = json.dumps(body, default=str).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else "{}"
            err_data = json.loads(err_body)
            status = err_data.get("status", "error")
            if status == "denied":
                error = err_data.get("error", {})
                raise BrokerDenied(
                    error.get("reason", "denied"),
                    error.get("policy_class", ""),
                )
            raise BrokerConnectionError(f"Broker HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise BrokerConnectionError(f"Broker unreachable: {e.reason}")

    def health(self) -> dict:
        """Check broker health."""
        try:
            url = f"{self._broker_url}/v1/health"
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    def send_action(self, action_type: str, target: str = "",
                    payload: Optional[dict] = None,
                    caller: Optional[dict] = None,
                    approval_token: Optional[dict] = None) -> dict:
        """Send a typed action request to the broker.

        Returns the response result dict, or raises BrokerDenied/BrokerConnectionError.
        """
        body = {
            "version": "hkp-v1",
            "request_id": self._request_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller or {"session_id": "unknown", "platform": "runtime", "origin": "hermes"},
            "action": {
                "type": action_type,
                "target": target,
                "payload": payload or {},
            },
        }
        if approval_token:
            body["approval"] = approval_token

        response = self._call_broker("/v1/action", body)
        return response.get("result", {})


# ── Convenience functions (for Hermes runtime code) ───────────────────────
_hkp_client: Optional[HKPClient] = None


def _get_client() -> HKPClient:
    global _hkp_client
    if _hkp_client is None:
        _hkp_client = HKPClient()
    return _hkp_client


def broker_health() -> dict:
    return _get_client().health()


def shadow_send(platform: str, target: str, content: dict,
                caller: Optional[dict] = None) -> dict:
    """Send a typed platform.send action to the broker (shadow mode)."""
    return _get_client().send_action(
        action_type=f"platform.send.{platform}",
        target=target,
        payload=content,
        caller=caller,
    )


def shadow_infer(model: str, messages: list, caller: Optional[dict] = None) -> dict:
    """Send a typed model.infer action to the broker (shadow mode)."""
    return _get_client().send_action(
        action_type="model.infer",
        target=model,
        payload={"model": model, "messages": messages},
        caller=caller,
    )
