# src/ - Pipeline Source Code

Core implementation of the VFV (Verify-Fix-Verify) pipeline.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `cli/` | Command-line interface entry point |
| `core/` | Configuration, database, models, telemetry, path safety |
| `pipeline/` | Orchestrator, error routing, classifiers |
| `services/` | Compilation, runtime, LLM, fixes, discovery, drift detection |
| `mcp_tools/` | MCP (Model Context Protocol) server interface |
| `utils/` | Markdown parsing utilities |

## Entry Points

- **CLI**: `python -m src.cli.main` - Primary pipeline entry point
- **MCP**: `python -m src.mcp_tools.server` - MCP server for IDE integration
