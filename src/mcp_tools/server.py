#!/usr/bin/env python3
"""
MCP Server for Example Reviewer Pipeline.
Exposes pipeline tools as MCP-compatible endpoints.
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .tools import ExampleReviewerTools, ToolResult, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP Server implementation for Example Reviewer Pipeline.
    
    Handles MCP protocol messages and routes to appropriate tools.
    Follows the MCP specification for tool registration and execution.
    """
    
    def __init__(
        self,
        config_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
    ):
        """
        Initialize MCP server.
        
        Args:
            config_dir: Path to family configs
            db_path: Path to database
            workspace_dir: Path to workspace
        """
        self.tools = ExampleReviewerTools(
            config_dir=config_dir,
            db_path=db_path,
            workspace_dir=workspace_dir,
        )

        # Protocol state
        self._initialized: bool = False
        self._client_info: Optional[Dict[str, Any]] = None

        # Map tool names to methods
        self._tool_handlers = {
            "scan": self.tools.scan,
            "extract": self.tools.extract,
            "compile_verify": self.tools.compile_verify,
            "compile_fix": self.tools.compile_fix,
            "runtime_verify": self.tools.runtime_verify,
            "runtime_fix": self.tools.runtime_fix,
            "md_update": self.tools.md_update,
            "final_review": self.tools.final_review,
            "commit": self.tools.commit,
            "backfill": self.tools.backfill,
            "status": self.tools.status,
            "run_pipeline": self.tools.run_pipeline,
            "validate_articles": self.tools.validate_articles,
            "validate_code_snippet": self.tools.validate_code_snippet,
        }
    
    def get_tools(self) -> list:
        """Return list of available tool definitions for MCP registration."""
        return TOOL_DEFINITIONS
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.
        
        Args:
            request: MCP request object with method, params
            
        Returns:
            MCP response object
        """
        method = request.get("method", "")
        params = request.get("params", {}) or {}
        request_id = request.get("id")

        # Notifications (no "id") must not receive a response per JSON-RPC spec
        is_notification = "id" not in request
        if is_notification and method.startswith("notifications/"):
            if method == "notifications/initialized":
                self._initialized = True
            logger.debug("Received notification: %s", method)
            return None

        if method == "initialize":
            self._client_info = params.get("clientInfo")
            client_version = params.get("protocolVersion", "2024-11-05")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": client_version,
                    "capabilities": {
                        "tools": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "example-reviewer",
                        "version": "0.1.0"
                    }
                }
            }

        elif method == "initialized":
            # Some clients send this as a method (not a notification path)
            self._initialized = True
            return None

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self.get_tools()}
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            result = self.call_tool(tool_name, arguments)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result.to_json()
                        }
                    ],
                    "isError": not result.success
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Call a tool by name with arguments.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            ToolResult from tool execution
        """
        handler = self._tool_handlers.get(tool_name)
        
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
        
        try:
            return handler(**arguments)
        except TypeError as e:
            return ToolResult(
                success=False,
                error=f"Invalid arguments: {e}"
            )
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def run_stdio(self) -> None:
        """
        Run server in stdio mode (for MCP protocol).
        Reads JSON-RPC requests from stdin, writes responses to stdout.
        """
        logger.info("Starting MCP server in stdio mode")
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {e}"
                    }
                }
                print(json.dumps(error_response), flush=True)
            
            except Exception as e:
                logger.exception("Error handling request")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}"
                    }
                }
                print(json.dumps(error_response), flush=True)


def main():
    """Entry point for MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Example Reviewer MCP Server")
    parser.add_argument('--config-dir', type=str, default='config/families')
    parser.add_argument('--db-path', type=str, default='data/example_reviewer.db')
    parser.add_argument('--workspace-dir', type=str, default='workspace')
    parser.add_argument('--verbose', '-v', action='store_true')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr,
    )
    
    server = MCPServer(
        config_dir=Path(args.config_dir),
        db_path=Path(args.db_path),
        workspace_dir=Path(args.workspace_dir),
    )
    
    server.run_stdio()


if __name__ == "__main__":
    main()
