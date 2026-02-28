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
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "config/families"))
DB_PATH = Path(os.getenv("DB_PATH", "data/example_reviewer.db"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "workspace"))
API_KEY = os.getenv("EXAMPLE_REVIEWER_API_KEY", "")
REQUEST_TIMEOUT = int(os.getenv("EXAMPLE_REVIEWER_REQUEST_TIMEOUT", "300"))
CORS_ORIGINS = os.getenv("EXAMPLE_REVIEWER_CORS_ORIGINS", "*").split(",")

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth middleware (optional — only active when EXAMPLE_REVIEWER_API_KEY is set)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not API_KEY:
        return await call_next(request)

    # Skip auth for health check
    if request.url.path == "/healthz":
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header == f"Bearer {API_KEY}":
        return await call_next(request)

    return Response(
        content=json.dumps({"error": "Unauthorized"}),
        status_code=401,
        media_type="application/json",
    )


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
