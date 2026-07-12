"""HKP Gateway interfaces — shadow mode for Phase A.

Each gateway:
  - Accepts typed action requests
  - Passes through to actual Hermes implementation (shadow mode)
  - Audits every request
  - Never returns credential material
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .audit_ledger import audit_event

logger = logging.getLogger("HKP.Gateways")


class ModelGateway:
    """LLM inference proxy.

    Phase A (shadow): receives request, logs it, returns success.
    No actual LLM call is made through this gateway in Phase A —
    Hermes still calls LLM providers directly.
    """

    def shadow_infer(self, model: str, messages: list, tools: Optional[list] = None,
                     request_id: str = "") -> dict:
        audit_event("model.infer", model,
                    "SHADOW_LOGGED", "shadow mode: request logged, no proxy call",
                    request_id=request_id)
        return {"status": "shadow", "message": "logged in shadow mode"}


class APIGateway:
    """External API proxy (Telegram, YouTube, X, TikTok, etc.).

    Phase A (shadow): receives request, logs it, returns success.
    No actual API call is made through this gateway in Phase A.
    """

    def shadow_send(self, platform: str, target: str, content: dict,
                    request_id: str = "") -> dict:
        audit_event(f"platform.send.{platform}", target,
                    "SHADOW_LOGGED", "shadow mode: request logged, no proxy call",
                    request_id=request_id)
        return {"status": "shadow", "message": "logged in shadow mode"}

    def shadow_upload(self, platform: str, target: str, media_info: dict,
                      request_id: str = "") -> dict:
        audit_event(f"platform.upload.{platform}", target,
                    "SHADOW_LOGGED", "shadow mode: upload logged",
                    request_id=request_id)
        return {"status": "shadow", "message": "logged in shadow mode"}


class DataGateway:
    """Data access proxy (DB, CRM, files).

    Phase A (shadow): receives request, logs it, returns success.
    No actual data operation through this gateway.
    """

    def shadow_read(self, source: str, query: str, fields: Optional[list] = None,
                    request_id: str = "") -> dict:
        audit_event("data.read", source,
                    "SHADOW_LOGGED", "shadow mode: read logged",
                    request_id=request_id)
        return {"status": "shadow", "message": "logged in shadow mode"}


# ── Singleton gateways ────────────────────────────────────────────────────
_model_gateway: Optional[ModelGateway] = None
_api_gateway: Optional[APIGateway] = None
_data_gateway: Optional[DataGateway] = None


def get_model_gateway() -> ModelGateway:
    global _model_gateway
    if _model_gateway is None:
        _model_gateway = ModelGateway()
    return _model_gateway


def get_api_gateway() -> APIGateway:
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway


def get_data_gateway() -> DataGateway:
    global _data_gateway
    if _data_gateway is None:
        _data_gateway = DataGateway()
    return _data_gateway
