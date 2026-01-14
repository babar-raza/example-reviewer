# Example Reviewer Pipeline - Implementation Summary

## Overview

This document summarizes the implementation of the Example Reviewer Pipeline system, which validates, fixes, and updates code examples in markdown documentation across multiple product families.

## Architecture

The system follows an MCP-first design with the following layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Tools Layer                         │
│  (ExampleReviewerTools - 11 independently executable tools) │
├─────────────────────────────────────────────────────────────┤
│                    Pipeline Orchestrator                     │
│     (Coordinates 6 phases: A → B → C → D → E → F)          │
├─────────────────────────────────────────────────────────────┤
│                      Services Layer                          │
│  Discovery │ Compilation │ Runtime │ LLM │ Markdown Update  │
├─────────────────────────────────────────────────────────────┤
│                       Core Layer                             │
│         Models │ Configuration │ Database                    │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
example_reviewer/
├── core/
│   ├── models.py          # Pydantic data models with state machine
│   ├── config.py          # Configuration system (global + per-family)
│   └── database.py        # SQLite database with WAL mode
├── services/
│   ├── discovery_service.py   # Phase A: Find and extract examples
│   ├── compilation_service.py # Phase B: Compile verification
│   ├── runtime_service.py     # Phase C: Runtime verification
│   ├── llm_service.py         # LLM adapter (OpenAI-compatible)
│   └── markdown_service.py    # Phase D: Update markdown files
├── pipeline/
│   └── orchestrator.py    # Full pipeline coordinator
├── mcp_tools/
│   ├── tools.py           # MCP tool implementations
│   └── server.py          # MCP server wrapper
├── cli/
│   └── main.py            # Command-line interface
└── vector_db/             # (Placeholder for embeddings)
```

## Configuration

### Global Config (config/global.json)
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_retries": 3
  },
  "git": { "enabled": false },
  "telemetry": { "local_telemetry_enabled": true }
}
```

### Family Config (config/families/zip.json)
```json
{
  "family": "zip",
  "content_roots": ["test-data/test-content"],
  "nuget_config": {
    "primary_package": { "name": "Aspose.Zip" }
  },
  "code_defaults": {
    "default_usings": ["Aspose.Zip", "Aspose.Zip.Saving"]
  },
  "runtime_validation": {
    "enabled": true,
    "mode": "lenient",
    "timeout_seconds": 30,
    "file_aliases": {
      "sample.zip": ["input.zip", "archive.zip"]
    }
  },
  "test_data": {
    "local_path": "test-data/test-data/zip"
  }
}
```

## MCP Tools

All operations are exposed as independently executable MCP tools:

| Tool | Description | Spec Phase |
|------|-------------|------------|
| `scan` | Find markdown files | A (partial) |
| `extract` | Extract code examples | A |
| `compile_verify` | Compile without LLM | B (partial) |
| `compile_fix` | Compile with LLM fixing | B |
| `runtime_verify` | Execute examples | C |
| `md_update` | Update markdown files | D |
| `final_review` | LLM review of updates | E |
| `commit` | Git commit changes | F |
| `backfill` | Fetch missing context | Utility |
| `status` | Get pipeline stats | Utility |
| `run_pipeline` | Execute full pipeline | All |

## Pipeline Phases

### Phase A: Discovery and Extraction
- Scans content roots for *.md files
- Extracts inline fenced code blocks (```cs, ```csharp)
- Extracts Hugo gist shortcodes ({{< gist owner id >}})
- Generates stable example IDs from content hashes
- Stores location metadata for safe replacement

### Phase B: Compilation Verification Loop
- Creates temporary .NET 8 projects
- Wraps code snippets in compilable structure
- Runs `dotnet restore` and `dotnet build`
- On failure: builds LLM fix payload with errors + API refs
- Retries up to max_retries from config

### Phase C: Runtime Verification Loop
- Executes compiled examples with test data
- Copies required files using aliases from config
- Captures stdout/stderr, exit codes, exceptions
- On failure: retrieves similar examples from vector DB
- Applies strict/lenient mode semantics

### Phase D: Markdown Update
- Replaces inline code blocks using location metadata
- Converts gist references to inline (or updates gist ID)
- Generates unified diffs for each file
- Supports dry-run mode

### Phase E: Final LLM Review
- Sends updated markdown to LLM for relevance check
- Validates code injection format
- Marks as FINAL_REVIEW_PASSED or FAILED

### Phase F: Persist, Telemetry, Commit
- Updates database with final status
- Writes telemetry records
- Git commits touched files (if enabled)

## Status State Machine

```
DISCOVERED ─────┬──────> COMPILE_FAILED
                │              │
                │              │ (LLM fix)
                │              ▼
                └──────> COMPILABLE ───┬──> RUNTIME_FAILED
                              │        │         │
                              │        │ (LLM fix)
                              │        ▼         │
                              │   VERIFIED <─────┘
                              │        │
                              └────────┴──> MD_UPDATED
                                                │
                              ┌─────────────────┴─────────────────┐
                              │                                   │
                              ▼                                   ▼
                    FINAL_REVIEW_PASSED              FINAL_REVIEW_FAILED
                              │
                              ▼
                         COMMITTED
```

## Multi-Family Support

The system supports multiple product families simultaneously:

- Each family has its own config file
- Database stores family field in all records
- Pipeline operations can filter by family
- Statistics available per-family or overall

### Configured Families (in test data)
- zip (Aspose.ZIP for .NET)
- cells (Aspose.Cells)
- pdf (Aspose.PDF)
- words (Aspose.Words)
- slides (Aspose.Slides)
- imaging (Aspose.Imaging)
- email (Aspose.Email)

## Usage

### CLI Commands
```bash
# List available families
python -m example_reviewer.cli.main list-families

# Extract examples for a family
python -m example_reviewer.cli.main extract --family zip --max-files 10

# Run full pipeline
python -m example_reviewer.cli.main run --family zip --dry-run

# Get status
python -m example_reviewer.cli.main status --family zip
```

### Python API
```python
from pathlib import Path
from example_reviewer.mcp_tools.tools import ExampleReviewerTools

tools = ExampleReviewerTools(
    config_dir=Path("config/families"),
    db_path=Path("data/example_reviewer.db"),
)

# Run individual phases
result = tools.extract(family="zip", max_files=10)
result = tools.compile_verify(family="zip")
result = tools.status(family="zip")

# Run full pipeline
result = tools.run_pipeline(
    family="zip",
    max_examples=50,
    skip_runtime=False,
    dry_run=True
)
```

### MCP Server
```bash
# Start MCP server in stdio mode
python -m example_reviewer.mcp_tools.server
```

## Test Data

The test data (from test.zip) includes:

- **test-content/**: 47 markdown files across blog, docs, kb sections
- **test-data/zip/**: 43 sample files (archives, text files)
- **test-reference/zip/**: API reference documentation
- **test-examples/**: C# validator project

## End-to-End Test Results

```
✓ Database CRUD operations work
✓ Global config loaded: LLM model = gpt-4o-mini
✓ Family config loaded: Aspose.ZIP for .NET
✓ Discovery service found 6 examples in test file
✓ Found 9 families: cells, email, imaging, pdf, slides, smoke, test, words, zip
✓ Scan found 42 markdown files
✓ Extract found 41 examples (20 inline, 21 gist)
✓ Status shows 41 DISCOVERED examples
```

## Dependencies

```
pydantic>=2.5.0
pydantic-settings>=2.1.0
openai>=1.0.0
requests>=2.31.0
```

## Notes

1. **Network Requirements**: Compilation requires network access to nuget.org for package restore
2. **LLM API Key**: Set OPENAI_API_KEY environment variable for LLM features
3. **Git Integration**: Set git.enabled=true in global config to enable commits
4. **Vector DB**: Placeholder exists for ChromaDB integration for similar example retrieval
