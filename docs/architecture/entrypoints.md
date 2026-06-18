# Entry Points

The system is exposed through two primary entry points:

1. CLI entry point: `src/cli/main.py`
2. MCP server entry point: `src/mcp_tools/server.py`

Both paths dispatch into the same `ExampleReviewerTools` layer, so the CLI,
MCP, and HTTP wrappers share the same core behavior.

## CLI

### Global Options

- `--config-dir` (default: `config/families`)
- `--db-path` (default: `data/example_reviewer.db`)
- `--workspace-dir` (default: `workspace`)
- `--verbose` / `-v`
- `--json`

### Primary Commands

- `scan`
- `extract`
- `compile-verify`
- `compile-fix`
- `runtime-verify`
- `runtime-fix`
- `md-update`
- `final-review`
- `commit`
- `run`
- `validate-articles`

### Additional Commands

- `list-families`
- `backfill`
- `clean-vector-db`
- `visualize-drift`
- `drift-trends`

### Markdown Write Guard

The `md-update` and `run` commands require explicit authorization before they
write markdown files:

- global config: `config/global.json` -> `markdown_write.allow_markdown_write`
- CLI flag: `--allow-md-write`

If not enabled, the markdown update phase behaves like a dry run.

### Content Roots Override

`scan`, `extract`, `run`, and `validate-articles` can override the family config's `content_roots`
without editing the JSON file:

```bash
PYTHONPATH=. python -m src.cli.main scan --family zip --content-roots C:/content/zip

PYTHONPATH=. python -m src.cli.main run --family zip \
    --content-roots C:/content/blog/zip C:/content/docs/zip

PYTHONPATH=. python -m src.cli.main validate-articles --family words \
    --content-roots D:/content/kb.aspose.net/words --audit-prose
```

### Article Validation and Prose Audit

- `validate-articles` runs deterministic article-structure checks and optional prose/code audits.
- `run --audit-prose` forwards the same prose audit into the markdown update phase for changed code blocks.
- `md-update --audit-prose` reuses the latest completed run and only audits prose adjacent to changed code blocks.

## MCP

The MCP server exposes tools via JSON-RPC over stdio:

- `tools/list`
- `tools/call`
- `initialize`
- `notifications/initialized`
- `ping`

### Tool Names

The MCP tool names mirror the CLI commands with underscore-style naming:

- `scan`
- `extract`
- `compile_verify`
- `compile_fix`
- `runtime_verify`
- `runtime_fix`
- `md_update`
- `final_review`
- `commit`
- `backfill`
- `status`
- `run_pipeline`
- `validate_articles`
- `validate_code_snippet`

### Deployment Model

The MCP server always runs as a local subprocess of the MCP client. That means:

- the server and client are on the same machine
- local content folders are directly accessible
- local `dotnet`, git, and SQLite resources are used directly

Example MCP override payload:

```json
{
  "name": "run_pipeline",
  "arguments": {
    "family": "zip",
    "content_roots": ["C:/content/blog/zip", "C:/content/docs/zip"]
  }
}
```

For the full protocol and HTTP wrapper details, see [MCP Server Reference](mcp.md).
