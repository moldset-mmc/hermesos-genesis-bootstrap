"""HKP Control Plane Broker Server — localhost HTTP API.

Dispatches typed action requests to the appropriate gateway,
always through policy evaluation and audit.

Phase A: shadow mode — all actions pass through, audits, returns results.
"""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional

from .schema import HKP_VERSION, ActionRequest, ActionResponse
from .audit_ledger import get_ledger, audit_event
from .policy_engine import get_engine, check_action
from .credential_store import get_store, verify_credential
from .gateways import get_model_gateway, get_api_gateway, get_data_gateway

logger = logging.getLogger("HKP.Broker")

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 9877
BROKER_MODE = os.environ.get("HKP_BROKER_MODE", "shadow")  # shadow | enforcing


class BrokerHandler(BaseHTTPRequestHandler):
    """HTTP handler for HKP Control Plane requests."""

    def log_message(self, format, *args):
        logger.debug("HTTP: %s", format % args)

    def _send_json(self, status_code: int, data: dict) -> None:
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-HKP-Version", HKP_VERSION)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        return json.loads(raw.decode("utf-8"))

    # ── Health ────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/v1/health":
            ledger = get_ledger()
            store = get_store()
            self._send_json(200, {
                "status": "ok",
                "version": HKP_VERSION,
                "mode": BROKER_MODE,
                "emergency_stop": os.environ.get("HKP_EMERGENCY_STOP", "false").lower() in ("true", "1"),
                "audit_count": ledger.count(),
                "credential_providers": store.health().get("provider_count", 0),
                "phase": "A",
            })
        elif self.path == "/v1/audit":
            ledger = get_ledger()
            limit = int(self.headers.get("X-Limit", 100))
            entries = ledger.query(limit=limit)
            self._send_json(200, {"entries": entries, "count": len(entries)})
        else:
            self._send_json(404, {"error": "not found"})

    # ── Action requests ──────────────────────────────────────────────
    def do_POST(self):
        request_id = "unknown"

        try:
            body = self._read_body()
            request = ActionRequest.from_dict(body)
            request_id = request.request_id or "unknown"

            # 1. Validate envelope
            err = request.validate()
            if err:
                response = ActionResponse.denied(request_id, "INVALID_REQUEST", err)
                self._send_json(400, response.to_dict())
                return

            action_type = request.action.get("type", "")
            target = request.action.get("target", "")
            payload = request.action.get("payload", {})

            # 2. Policy check
            policy_result = check_action(
                action_type=action_type,
                target=target,
                caller={"request_id": request_id, **request.caller},
                approval_token=request.approval,
            )

            if not policy_result["allowed"]:
                response = ActionResponse.denied(
                    request_id,
                    "BLOCKED_BY_HKP",
                    policy_result["reason"],
                    policy_class=policy_result["policy_class"],
                )
                self._send_json(403, response.to_dict())
                return

            # 3. Dispatch to appropriate gateway
            result = self._dispatch_action(action_type, target, payload, request_id)

            # 4. Respond
            audit = {"audit_id": f"aud_{request_id[:16]}", "policy_class": policy_result["policy_class"]}
            response = ActionResponse.ok(request_id, result=result, audit=audit)
            self._send_json(200, response.to_dict())

        except json.JSONDecodeError:
            response = ActionResponse.denied(request_id, "INVALID_JSON", "invalid JSON body")
            self._send_json(400, response.to_dict())
        except Exception as exc:
            logger.error("Request failed: %s\n%s", exc, traceback.format_exc())
            response = ActionResponse.error(request_id, str(exc))
            self._send_json(500, response.to_dict())

    def _dispatch_action(self, action_type: str, target: str, payload: dict,
                         request_id: str) -> dict:
        """Dispatch to the appropriate gateway based on action type prefix."""
        if action_type.startswith("model."):
            return get_model_gateway().shadow_infer(
                model=target or payload.get("model", "unknown"),
                messages=payload.get("messages", []),
                tools=payload.get("tools"),
                request_id=request_id,
            )

        if action_type.startswith("platform."):
            if "upload" in action_type:
                return get_api_gateway().shadow_upload(
                    platform=payload.get("platform", target),
                    target=payload.get("target", ""),
                    media_info=payload,
                    request_id=request_id,
                )
            return get_api_gateway().shadow_send(
                platform=payload.get("platform", target),
                target=payload.get("target", ""),
                content=payload,
                request_id=request_id,
            )

        if action_type.startswith("data."):
            if action_type == "data.write":
                audit_event("data.write", target, "SHADOW_LOGGED",
                            "shadow mode: write logged, no proxy call",
                            request_id=request_id)
                return {"status": "shadow", "message": "write logged"}
            return get_data_gateway().shadow_read(
                source=target,
                query=payload.get("query", ""),
                fields=payload.get("fields"),
                request_id=request_id,
            )

        if action_type == "credential.verify":
            provider = payload.get("provider", target)
            has_creds = verify_credential(provider)
            return {"status": "ok", "has_credentials": has_creds}

        if action_type == "policy.check":
            from .policy_engine import check_action
            sub_action = payload.get("action", "")
            sub_target = payload.get("target", "")
            result = check_action(sub_action, sub_target, {"request_id": request_id})
            return {"policy_result": result}

        if action_type == "audit.query":
            ledger = get_ledger()
            entries = ledger.query(
                limit=payload.get("limit", 100),
                action_filter=payload.get("action_filter"),
                since=payload.get("since"),
            )
            return {"entries": entries, "count": len(entries)}

        return {"status": "unknown_action", "action_type": action_type}


# ── Server startup ────────────────────────────────────────────────────────
def start_broker(host: str = BROKER_HOST, port: int = BROKER_PORT,
                 mode: str = BROKER_MODE) -> HTTPServer:
    """Start the Control Plane broker HTTP server."""
    global BROKER_MODE
    BROKER_MODE = mode

    server = HTTPServer((host, port), BrokerHandler)
    logger.info("HKP Control Plane Broker starting on %s:%d (mode=%s, phase=A)", host, port, mode)
    return server


def run_broker_forever(host: str = BROKER_HOST, port: int = BROKER_PORT,
                       mode: str = BROKER_MODE) -> None:
    """Start and run broker forever (blocking)."""
    server = start_broker(host, port, mode)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Broker shutting down")
        server.shutdown()
