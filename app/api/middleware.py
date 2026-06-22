"""
Custom middleware for the IUNA API.
"""

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-Id to every request/response cycle.

    If the incoming request already carries an X-Request-Id header, it is
    preserved; otherwise a new UUID is generated.  The value is stored in
    ``request.state.request_id`` and echoed back in the response header.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
