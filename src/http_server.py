"""
HTTP API server for Example Reviewer Pipeline.

Thin FastAPI wrapper around MCPServer.call_tool() — exposes all MCP tools
over HTTP REST so external agents (seo-intelligence, etc.) can call them.

Launch:
    uvicorn src.http_server:app --host 0.0.0.0 --port 18800
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.authority import Capability, PolicyDecisionPoint
from .core.authority.policies.http_boundary import http_access_policy, validate_cors_config
from .mcp_tools.server import MCPServer
from .mcp_tools.tools import TOOL_DEFINITIONS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _parse_bounded_int_env(name: str, default: int, min_value: int, max_value: int) -> int:
    """Parse an integer env var with a safe fallback and clamped bounds (TC-EPIC1-06).

    Replaces the old bare ``int(os.getenv(...))`` which crashed the whole process
    at import time on a malformed value, and accepted 0/negative values unchecked.
    """
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("%s=%r is not a valid integer; falling back to default %d", name, raw, default)
        return default
    if value < min_value or value > max_value:
        clamped = max(min_value, min(max_value, value))
        logger.warning(
            "%s=%d is out of bounds [%d, %d]; clamping to %d", name, value, min_value, max_value, clamped
        )
        return clamped
    return value


class _TokenBucket:
    """In-process, per-key token bucket rate limiter (TC-EPIC1-06).

    No external dependency (no Redis/slowapi) -- acceptable per this taskcard's
    explicit non-goals, given the single-``uvicorn``-process deployment model in
    docker-compose.yml (no multi-replica orchestration configured).
    """

    def __init__(self, capacity: float, refill_per_second: float) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._state: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = _time.monotonic()
        with self._lock:
            tokens, last = self._state.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill_per_second)
            if tokens < 1.0:
                self._state[key] = (tokens, now)
                return False
            self._state[key] = (tokens - 1.0, now)
            return True

    def reset(self) -> None:
        """Test-only: clear all per-key state."""
        with self._lock:
            self._state.clear()


# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "config/families"))
DB_PATH = Path(os.getenv("DB_PATH", "data/example_reviewer.db"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "workspace"))
API_KEY = os.getenv("EXAMPLE_REVIEWER_API_KEY", "")
DEV_MODE = os.getenv("EXAMPLE_REVIEWER_DEV_MODE", "").strip().lower() in ("1", "true", "yes", "on")
REQUEST_TIMEOUT = _parse_bounded_int_env("EXAMPLE_REVIEWER_REQUEST_TIMEOUT", 300, 1, 3600)
MAX_BODY_BYTES = _parse_bounded_int_env("EXAMPLE_REVIEWER_MAX_BODY_BYTES", 10 * 1024 * 1024, 1024, 1024 * 1024 * 1024)
RATE_LIMIT_PER_MINUTE = _parse_bounded_int_env("EXAMPLE_REVIEWER_RATE_LIMIT_PER_MINUTE", 300, 1, 1_000_000)
RATE_LIMIT_BURST = _parse_bounded_int_env("EXAMPLE_REVIEWER_RATE_LIMIT_BURST", 60, 1, 1_000_000)

CORS_ORIGINS = [origin.strip() for origin in os.getenv("EXAMPLE_REVIEWER_CORS_ORIGINS", "*").split(",")]
# Fail-closed default: a wildcard origin list disables credentialed CORS
# automatically (no startup crash for the common/default case). An operator who
# wants credentials with a wildcard origin must opt in explicitly, at which point
# validate_cors_config() below refuses to start -- see http_boundary.py's
# module docstring for why this is a plain startup check rather than a per-request
# PDP capability.
_CORS_ALLOW_CREDENTIALS_REQUESTED = os.getenv("EXAMPLE_REVIEWER_CORS_ALLOW_CREDENTIALS", "").strip().lower() in (
    "1", "true", "yes", "on",
)
ALLOW_CREDENTIALS = _CORS_ALLOW_CREDENTIALS_REQUESTED or "*" not in CORS_ORIGINS
validate_cors_config(CORS_ORIGINS, ALLOW_CREDENTIALS)

# ---------------------------------------------------------------------------
# Authorization Kernel (TC-EPIC1-06): every boundary decision -- auth, rate
# limit, body size -- is computed by http_access_policy via this PDP instance,
# so all three are audited under one capability with distinguishing policy_ids.
# ---------------------------------------------------------------------------
_http_pdp = PolicyDecisionPoint()
_http_pdp.register_policy(Capability.HTTP_ACCESS, http_access_policy)
_rate_limiter = _TokenBucket(capacity=RATE_LIMIT_BURST, refill_per_second=RATE_LIMIT_PER_MINUTE / 60.0)

_POLICY_ID_STATUS = {
    "http.rate_limit.exceeded": 429,
    "http.body_size.exceeded": 413,
    "http.auth.no_key_configured": 503,
    "http.auth.invalid_key": 401,
}


def _decision_to_response(decision) -> Response:
    status_code = _POLICY_ID_STATUS.get(decision.policy_id, 403)
    return Response(
        content=json.dumps({"error": decision.reason, "policy_id": decision.policy_id}),
        status_code=status_code,
        media_type="application/json",
    )


def _client_key(request: Request) -> str:
    client = request.client
    return client.host if client else "unknown"


# ---------------------------------------------------------------------------
# Thread pool for blocking tool calls (dotnet subprocess, DB queries)
# ---------------------------------------------------------------------------
_executor = ThreadPoolExecutor(max_workers=4)

# ---------------------------------------------------------------------------
# MCP Server (singleton, lazy orchestrator inside)
# ---------------------------------------------------------------------------
mcp_server = MCPServer(
    config_dir=CONFIG_DIR,
    db_path=DB_PATH,
    workspace_dir=WORKSPACE_DIR,
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Example Reviewer API",
    version="1.0.0",
    description="HTTP API exposing Example Reviewer MCP tools for external agents.",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# HTTP boundary middleware (TC-EPIC1-06): fails CLOSED by default -- an unset
# EXAMPLE_REVIEWER_API_KEY now refuses service (503) instead of serving every
# route unauthenticated, unless EXAMPLE_REVIEWER_DEV_MODE=true is explicitly
# set. /healthz always bypasses every check (container healthcheck must keep
# working regardless of auth state). Every decision is computed by
# http_access_policy via _http_pdp.check() -- this function is a thin adapter
# translating Decision -> HTTP response, per TC-EPIC1-06's design.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path == "/healthz":
        return await call_next(request)

    rate_decision = _http_pdp.check(
        Capability.HTTP_ACCESS,
        resource=path,
        context={"check": "rate_limit", "rate_limited": not _rate_limiter.allow(_client_key(request))},
    )
    if not rate_decision.allow:
        return _decision_to_response(rate_decision)

    content_length = request.headers.get("content-length")
    body_size = int(content_length) if content_length is not None and content_length.isdigit() else None
    body_decision = _http_pdp.check(
        Capability.HTTP_ACCESS,
        resource=path,
        context={"check": "body_size", "body_size": body_size, "max_body_bytes": MAX_BODY_BYTES},
    )
    if not body_decision.allow:
        return _decision_to_response(body_decision)

    auth_header = request.headers.get("Authorization", "")
    auth_decision = _http_pdp.check(
        Capability.HTTP_ACCESS,
        resource=path,
        context={"check": "auth", "api_key": API_KEY, "auth_header": auth_header, "dev_mode": DEV_MODE},
    )
    if not auth_decision.allow:
        return _decision_to_response(auth_decision)

    if auth_decision.policy_id == "http.auth.dev_mode_open":
        logger.warning(
            "EXAMPLE_REVIEWER_DEV_MODE is enabled: serving %s %s with NO authentication. "
            "Do not use this setting in production.",
            request.method,
            path,
        )

    return await call_next(request)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class ValidateCodeRequest(BaseModel):
    code: str
    family: str
    language: str = "csharp"
    compile_verify: bool = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/api/v1/tools")
async def list_tools():
    """Return available tool definitions (for agent discovery)."""
    return {"tools": TOOL_DEFINITIONS}


@app.post("/api/v1/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """
    Generic tool invocation — delegates to MCPServer.call_tool().

    Body: JSON dict of tool arguments.
    Returns: ToolResult as JSON.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                partial(mcp_server.call_tool, tool_name, body),
            ),
            timeout=REQUEST_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"Tool '{tool_name}' timed out after {REQUEST_TIMEOUT}s")

    return json.loads(result.to_json())


@app.post("/api/v1/validate-code")
async def validate_code(req: ValidateCodeRequest):
    """
    Convenience endpoint for code snippet validation.

    Shortcut for POST /api/v1/tools/validate_code_snippet with a typed request body.
    """
    args = {
        "code": req.code,
        "family": req.family,
        "language": req.language,
        "compile_verify": req.compile_verify,
    }

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                _executor,
                partial(mcp_server.call_tool, "validate_code_snippet", args),
            ),
            timeout=REQUEST_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Validation timed out")

    return json.loads(result.to_json())
