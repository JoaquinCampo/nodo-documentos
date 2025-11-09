from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Simple header-based API key enforcement."""

    def __init__(
        self,
        app,
        *,
        api_key: str | None,
        header_name: str = "x-api-key",
    ) -> None:
        super().__init__(app)
        self._api_key = api_key
        self._header_name = header_name
        # Paths that don't require API key
        self._public_paths = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._public_paths:
            return await call_next(request)

        if not self._api_key:
            return await call_next(request)

        provided = request.headers.get(self._header_name)
        if provided != self._api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)


__all__ = ["APIKeyMiddleware"]
