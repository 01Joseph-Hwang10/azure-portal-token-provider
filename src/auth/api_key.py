from typing import cast

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import Settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        received = request.headers.get("X-Api-Key", None)
        expected = cast(Settings, request.app.settings).api_key
        if expected is not None and received != expected:
            return JSONResponse(
                status_code=403,
                content={"message": "Forbidden"},
            )
        response = await call_next(request)
        return response
