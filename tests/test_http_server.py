"""Tests for the HTTP API server (src/http_server.py)."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from src.mcp_tools.tools import ToolResult


@pytest.fixture
def client():
    """Create a FastAPI TestClient with mocked MCP server."""
    # Must patch before importing the module (module-level initialization)
    with patch("src.http_server.mcp_server") as mock_server:
        # Default mock: call_tool returns a successful ToolResult
        mock_server.call_tool.return_value = ToolResult(
            success=True,
            data={"valid": True, "hallucinated_types": [], "namespace_violations": []},
        )
        mock_server.get_tools.return_value = [
            {"name": "status", "description": "Get pipeline status"},
            {"name": "validate_code_snippet", "description": "Validate code"},
        ]

        from fastapi.testclient import TestClient
        from src.http_server import app

        yield TestClient(app), mock_server


class TestHealthz:
    def test_healthz_returns_ok(self, client):
        tc, _ = client
        resp = tc.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestListTools:
    def test_list_tools_returns_definitions(self, client):
        tc, _ = client
        resp = tc.get("/api/v1/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        # Should return all 13 tool definitions (12 original + validate_code_snippet)
        assert len(data["tools"]) == 13
        tool_names = [t["name"] for t in data["tools"]]
        assert "scan" in tool_names
        assert "validate_code_snippet" in tool_names
        assert "run_pipeline" in tool_names


class TestCallTool:
    def test_call_tool_success(self, client):
        tc, mock_server = client
        resp = tc.post("/api/v1/tools/status", json={"family": "zip"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_server.call_tool.assert_called_once_with("status", {"family": "zip"})

    def test_call_tool_empty_body(self, client):
        tc, mock_server = client
        resp = tc.post("/api/v1/tools/status")
        assert resp.status_code == 200
        mock_server.call_tool.assert_called_once()

    def test_call_tool_unknown_returns_error(self, client):
        tc, mock_server = client
        mock_server.call_tool.return_value = ToolResult(
            success=False, error="Unknown tool: foobar"
        )
        resp = tc.post("/api/v1/tools/foobar", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Unknown tool" in data["error"]


class TestValidateCode:
    def test_validate_code_shortcut(self, client):
        tc, mock_server = client
        resp = tc.post(
            "/api/v1/validate-code",
            json={"code": "var x = new Archive();", "family": "zip"},
        )
        assert resp.status_code == 200
        mock_server.call_tool.assert_called_once_with(
            "validate_code_snippet",
            {
                "code": "var x = new Archive();",
                "family": "zip",
                "language": "csharp",
                "compile_verify": False,
            },
        )

    def test_validate_code_missing_required_field(self, client):
        tc, _ = client
        resp = tc.post("/api/v1/validate-code", json={"code": "hello"})
        assert resp.status_code == 422  # Pydantic validation error

    def test_validate_code_custom_language(self, client):
        tc, mock_server = client
        resp = tc.post(
            "/api/v1/validate-code",
            json={"code": "import aspose", "family": "words", "language": "python"},
        )
        assert resp.status_code == 200
        call_args = mock_server.call_tool.call_args[0]
        assert call_args[1]["language"] == "python"


class TestAuthMiddleware:
    def test_no_auth_when_key_not_set(self, client):
        """When EXAMPLE_REVIEWER_API_KEY is empty, all requests pass."""
        tc, _ = client
        resp = tc.get("/api/v1/tools")
        assert resp.status_code == 200

    def test_auth_required_when_key_set(self):
        """When API key is set, requests without Bearer token get 401."""
        with patch.dict(os.environ, {"EXAMPLE_REVIEWER_API_KEY": "secret123"}):
            with patch("src.http_server.API_KEY", "secret123"):
                with patch("src.http_server.mcp_server") as mock_server:
                    mock_server.get_tools.return_value = []

                    from fastapi.testclient import TestClient
                    from src.http_server import app

                    tc = TestClient(app)

                    # Without token -> 401
                    resp = tc.get("/api/v1/tools")
                    assert resp.status_code == 401

                    # With correct token -> 200
                    resp = tc.get(
                        "/api/v1/tools",
                        headers={"Authorization": "Bearer secret123"},
                    )
                    assert resp.status_code == 200

    def test_healthz_bypasses_auth(self):
        """Health check should always work regardless of auth."""
        with patch("src.http_server.API_KEY", "secret123"):
            with patch("src.http_server.mcp_server"):
                from fastapi.testclient import TestClient
                from src.http_server import app

                tc = TestClient(app)
                resp = tc.get("/healthz")
                assert resp.status_code == 200
