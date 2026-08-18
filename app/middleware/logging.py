"""Structured JSON request logging middleware."""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as a single JSON line (correlation id included)."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
                ensure_ascii=False,
            )
        )
        return response