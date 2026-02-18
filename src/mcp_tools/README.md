# src/mcp_tools/ - MCP Server Interface

Model Context Protocol (MCP) server for IDE integration (e.g., Claude Code, VS Code).

## Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server implementation (JSON-RPC over stdio) |
| `tools.py` | Tool definitions and implementations exposed via MCP |

## Usage

```bash
python -m src.mcp_tools.server
```

Exposes pipeline operations as MCP tools: discover, compile, verify, fix, commit, status.
