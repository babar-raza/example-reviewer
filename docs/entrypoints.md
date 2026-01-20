# Entry Points

The system is exposed through two primary entry points:

1. **CLI Entry Point**
   - File: `src/cli/main.py`
   - The CLI constructs an `ExampleReviewerTools` instance and dispatches subcommands.

2. **MCP Server Entry Point**
   - File: `src/mcp_tools/server.py`
   - The MCP server exposes tools via JSON-RPC.

## CLI Entry Point

### Global CLI Options

- `--config-dir`: Defaults to `config/families`
- `--db-path`: Defaults to `data/example_reviewer.db`
- `--workspace-dir`: Defaults to `workspace`
- `--verbose` / `-v`
- `--json`: Print tool output in JSON format

### Primary Subcommands

These subcommands map to pipeline phases:

- `scan`: Locate markdown files to process
- `extract`: Extract code blocks and gist references (Phase A)
- `compile-verify`: Compile examples without LLM fixes (Phase B)
- `compile-fix`: Compile examples with LLM fixes (Phase B)
- `runtime-verify`: Execute examples without LLM fixes (Phase C)
- `runtime-fix`: Execute examples with LLM fixes (Phase C)
- `md-update`: Apply verified code back to markdown files (Phase D)
- `final-review`: LLM review of updated markdown (Phase E)
- `commit`: Commit changes (Phase F)
- `run`: Run the full pipeline end-to-end

### Additional Operational Subcommands

- `list-families`
- `backfill`: Populate missing API refs, test data, examples, and gist source
- `clean-vector-db`: Remove high-drift examples from the vector DB
- `visualize-drift`
- `drift-trends`

### Safety Guard: Markdown Writes

The `md-update` and `run` subcommands require explicit authorization to write markdown:

- Global config: `config/global.json` -> `markdown_write.allow_markdown_write: true`
- CLI flag: `--allow-md-write`

If not enabled, the markdown update phase is treated as a dry-run, and any actual write will raise `MarkdownWriteGuardError`.

## MCP Server Entry Point

The MCP server exposes tools via JSON-RPC:

- `tools/list`: Returns tool definitions
- `tools/call`: Runs a tool with structured arguments

Tools are implemented by `ExampleReviewerTools` in `src/mcp_tools/tools.py`.

### Tool Surface

Tool names are camel/underscore variants of the CLI commands:

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

## Recommended Run Patterns

Because this archive is missing packaging metadata, these examples assume you run from the repo root and set `PYTHONPATH` so `src/` resolves as a package.

- **CLI as module**:
  ```bash
  PYTHONPATH=. python -m src.cli.main list-families
  ```

- **MCP server as module**:
  ```bash
  PYTHONPATH=. python -m src.mcp_tools.server --verbose