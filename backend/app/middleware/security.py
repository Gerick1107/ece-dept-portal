"""HTTP security headers and basic rate limiting (OWASP-aligned)."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

# Common non-browser automation / scripting clients we block from the API.
_BLOCKED_AGENT_RE = re.compile(
    r"(curl|wget|python-requests|httpx|aiohttp|postman|insomnia|libwww|"
    r"lwp::simple|java/|okhttp|go-http-client|scrapy|httpie|winhttp|"
    r"powershell|restsharp|guzzle|axios/|node-fetch)",
    re.IGNORECASE,
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "0"
        if get_settings().app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        return response


class BlockedUserAgentMiddleware(BaseHTTPMiddleware):
    """Reject API requests from common scripting/automation clients.

    Only applies to the API prefix so browser traffic and static assets are
    unaffected. A missing/empty User-Agent is also blocked for API calls.
    """

    def __init__(self, app, api_prefix: str = "/api"):
        super().__init__(app)
        self.api_prefix = api_prefix

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if get_settings().block_automation_agents and request.url.path.startswith(self.api_prefix):
            ua = request.headers.get("user-agent", "")
            if not ua or _BLOCKED_AGENT_RE.search(ua):
                return JSONResponse(status_code=403, content={"detail": "Forbidden client."})
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP sliding-window rate limiting at second / minute / hour scales.

    In-memory (per worker process). For multi-worker or multi-host deployments
    this is a first line of defence; nginx ``limit_req`` provides an edge layer.
    """

    def __init__(self, app, api_prefix: str = "/api"):
        super().__init__(app)
        self.api_prefix = api_prefix
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled or not request.url.path.startswith(self.api_prefix):
            return await call_next(request)

        key = _client_ip(request)
        now = time.time()
        hits = self._hits[key]
        # Drop timestamps older than one hour (the largest window we track).
        while hits and now - hits[0] > 3600:
            hits.popleft()

        per_sec = sum(1 for t in hits if now - t < 1)
        per_min = sum(1 for t in hits if now - t < 60)
        per_hour = len(hits)
        if (
            per_sec >= settings.rate_limit_per_second
            or per_min >= settings.rate_limit_per_minute
            or per_hour >= settings.rate_limit_per_hour
        ):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={"Retry-After": "1"},
            )
        hits.append(now)
        return await call_next(request)


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """Throttle brute-force attempts on both login endpoints (per IP)."""

    def __init__(self, app, max_attempts: int | None = None, window_seconds: int | None = None):
        super().__init__(app)
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        is_login = request.method == "POST" and (
            path.endswith("/auth/login") or path.endswith("/auth/login/json")
        )
        if is_login:
            settings = get_settings()
            max_attempts = self._max_attempts or settings.login_max_attempts
            window_seconds = self._window_seconds or settings.login_window_seconds
            key = _client_ip(request)
            now = time.time()
            window = [t for t in self._hits[key] if now - t < window_seconds]
            if len(window) >= max_attempts:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many login attempts. Please try again later."},
                )
            window.append(now)
            self._hits[key] = window
        return await call_next(request)
