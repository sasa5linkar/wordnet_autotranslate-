"""Structured observability helpers for translation workflows."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional


def ensure_request_id(request_id: Optional[str] = None) -> str:
    """Return a stable correlation id (generate one when omitted)."""
    if request_id and str(request_id).strip():
        return str(request_id).strip()
    return str(uuid.uuid4())


def get_structured_logger(name: str = "wordnet_autotranslate") -> logging.Logger:
    """Create or return a logger configured for line-delimited JSON logs."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def log_event(
    logger: logging.Logger,
    *,
    event: str,
    request_id: str,
    stage: Optional[str] = None,
    level: str = "info",
    **fields: Any,
) -> None:
    """Emit a structured JSON log line with correlation metadata."""
    payload: Dict[str, Any] = {"event": event, "request_id": request_id}
    if stage:
        payload["stage"] = stage
    payload.update(fields)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    log_fn = getattr(logger, level, logger.info)
    log_fn(line)
