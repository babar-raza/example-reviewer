"""Tests for MCPServer JSON-RPC 2.0 protocol compliance."""
import json
import io
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.mcp_tools.tools import ToolResult, TOOL_DEFINITIONS
from src.mcp_tools.server import MCPServer


@pytest.fixture
def mock_tools():
    """Create mock ExampleReviewerTools."""
    tools = MagicMock()
    tools.scan.return_value = ToolResult(success=True, data={"mode": "directory", "file_count": 3})
    tools.extract.return_value = ToolResult(success=True, data={"examples_found": 10})
    tools.status.return_value = ToolResult(success=True, data={"family": "zip"})
    return tools


@pytest.fixture
def server(mock_tools):
    """Create MCPServer with mocked tools (bypass ExampleReviewerTools constructor)."""
    with patch.object(MCPServer, '__init__', lambda self, **kwargs: None):
        srv = MCPServer()
    srv.tools = mock_tools
    srv._initialized = False
    srv._client_info = None
    srv._tool_handlers = {
        "scan": mock_tools.scan,
        "extract": mock_tools.extract,
        "compile_verify": mock_tools.compile_verify,
        "compile_fix": mock_tools.compile_fix,
        "runtime_verify": mock_tools.runtime_verify,
        "runtime_fix": mock_tools.runtime_fix,
        "md_update": mock_tools.md_update,
        "final_review": mock_tools.final_review,
        "commit": mock_tools.commit,
        "backfill": mock_tools.backfill,
        "status": mock_tools.status,
        "run_pipeline": mock_tools.run_pipeline,
    }
    return srv


class TestInitialize:
    def test_initialize_response_format(self, server):
        """Initialize returns proper MCP handshake response."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "test-client", "version": "1.0"},
            "capabilities": {},
        }}
        response = server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        result = response["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "example-reviewer"
        assert result["serverInfo"]["version"] == "0.1.0"

    def test_initialize_stores_client_info(self, server):
        """Initialize stores client info on server."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "my-client", "version": "2.0"},
            "capabilities": {},
        }}
        server.handle_request(request)
        assert server._client_info == {"name": "my-client", "version": "2.0"}


class TestToolsList:
    def test_tools_list_returns_definitions(self, server):
        """tools/list returns all TOOL_DEFINITIONS."""
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        tools = response["result"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) == len(TOOL_DEFINITIONS)

    def test_tools_list_has_all_required_fields(self, server):
        """Each tool in list has name, description, inputSchema."""
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
        response = server.handle_request(request)
        for tool in response["result"]["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool


class TestToolsCall:
    def test_call_routes_correctly(self, server, mock_tools):
        """tools/call routes to the correct handler."""
        request = {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "scan", "arguments": {"directory": "/tmp"},
        }}
        response = server.handle_request(request)
        assert response["id"] == 4
        assert response["result"]["isError"] is False
        content = response["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        mock_tools.scan.assert_called_once_with(directory="/tmp")

    def test_call_success_is_error_false(self, server, mock_tools):
        """Successful tool call has isError: false."""
        mock_tools.status.return_value = ToolResult(success=True, data={})
        request = {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
            "name": "status", "arguments": {},
        }}
        response = server.handle_request(request)
        assert response["result"]["isError"] is False

    def test_call_failure_is_error_true(self, server, mock_tools):
        """Failed tool call has isError: true."""
        mock_tools.status.return_value = ToolResult(success=False, error="failed")
        request = {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
            "name": "status", "arguments": {},
        }}
        response = server.handle_request(request)
        assert response["result"]["isError"] is True

    def test_call_preserves_request_id(self, server, mock_tools):
        """Response echoes the request ID."""
        request = {"jsonrpc": "2.0", "id": 42, "method": "tools/call", "params": {
            "name": "status", "arguments": {},
        }}
        response = server.handle_request(request)
        assert response["id"] == 42

    def test_call_unknown_tool(self, server):
        """Calling unknown tool returns error."""
        request = {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {
            "name": "nonexistent_tool", "arguments": {},
        }}
        response = server.handle_request(request)
        result = response["result"]
        assert result["isError"] is True
        content_text = result["content"][0]["text"]
        assert "Unknown tool" in content_text

    def test_call_invalid_args(self, server, mock_tools):
        """Invalid arguments (TypeError) returns error."""
        mock_tools.extract.side_effect = TypeError("missing required argument: 'family'")
        request = {"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {
            "name": "extract", "arguments": {},
        }}
        response = server.handle_request(request)
        result = response["result"]
        assert result["isError"] is True
        content_text = result["content"][0]["text"]
        assert "Invalid arguments" in content_text

    def test_call_tool_exception(self, server, mock_tools):
        """Unhandled exception in tool returns error without crashing."""
        mock_tools.extract.side_effect = RuntimeError("unexpected crash")
        request = {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {
            "name": "extract", "arguments": {"family": "zip"},
        }}
        response = server.handle_request(request)
        result = response["result"]
        assert result["isError"] is True

    def test_call_content_is_valid_json(self, server, mock_tools):
        """Content text is parseable JSON."""
        request = {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {
            "name": "status", "arguments": {},
        }}
        response = server.handle_request(request)
        content_text = response["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed


class TestErrorHandling:
    def test_unknown_method_returns_32601(self, server):
        """Unknown method returns JSON-RPC -32601."""
        request = {"jsonrpc": "2.0", "id": 11, "method": "unknown/method", "params": {}}
        response = server.handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    def test_error_preserves_id(self, server):
        """Error response echoes the request ID."""
        request = {"jsonrpc": "2.0", "id": 99, "method": "bad/method", "params": {}}
        response = server.handle_request(request)
        assert response["id"] == 99


class TestPing:
    def test_ping_returns_empty_result(self, server):
        """Ping returns empty result (keep-alive)."""
        request = {"jsonrpc": "2.0", "id": 12, "method": "ping", "params": {}}
        response = server.handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 12
        assert response["result"] == {}


class TestNotifications:
    def test_initialized_notification_returns_none(self, server):
        """notifications/initialized is handled and returns None (no response)."""
        request = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        response = server.handle_request(request)
        assert response is None
        assert server._initialized is True

    def test_cancelled_notification_returns_none(self, server):
        """notifications/cancelled is handled gracefully."""
        request = {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {
            "requestId": 5, "reason": "user cancelled",
        }}
        response = server.handle_request(request)
        assert response is None


class TestStdioProtocol:
    def test_run_stdio_processes_request(self, server):
        """run_stdio reads JSON from stdin, writes response to stdout."""
        request_json = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})

        with patch('sys.stdin', io.StringIO(request_json + "\n")):
            with patch('builtins.print') as mock_print:
                server.run_stdio()

        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        parsed = json.loads(output)
        assert parsed["id"] == 1
        assert parsed["result"] == {}

    def test_run_stdio_skips_notification_response(self, server):
        """Notifications don't produce output on stdout."""
        request_json = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        with patch('sys.stdin', io.StringIO(request_json + "\n")):
            with patch('builtins.print') as mock_print:
                server.run_stdio()

        mock_print.assert_not_called()

    def test_run_stdio_handles_malformed_json(self, server):
        """Malformed JSON produces -32700 error."""
        with patch('sys.stdin', io.StringIO("not valid json\n")):
            with patch('builtins.print') as mock_print:
                server.run_stdio()

        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        parsed = json.loads(output)
        assert parsed["error"]["code"] == -32700
