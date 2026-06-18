<!-- merged-from: overview.md, pipeline.md -->

# Pipeline Overview

The Example Reviewer pipeline extracts, validates, and updates code examples embedded in markdown documentation. It ensures that code snippets are compilable, executable, and consistent with their intended functionality.

## Key Features

- **Discovery and Extraction**: Locates and extracts code snippets from markdown files.
- **Compilation and Runtime Verification**: Validates code snippets for compilation and runtime correctness.
- **LLM-Based Fixes**: Uses Large Language Models (LLMs) to fix compilation and runtime errors.
- **Markdown Updates**: Safely updates markdown files with verified code snippets.
- **Telemetry and Artifacts**: Tracks pipeline execution and stores artifacts for debugging and analysis.

## Core Entities

The main coordinator is `src/pipeline/orchestrator.py` (`PipelineOrchestrator`).

- **ExampleRecord** (`src/core/models.py`): Represents one code snippet (inline code fence) or a gist reference discovered in a markdown file.
- **CompileAttempt**: Records each compilation attempt.
- **RuntimeAttempt**: Records each execution attempt.
- **MarkdownEdit**: Records markdown file updates.
- **RunRecord**: Records each pipeline run.

A simple state machine is used for examples (`ExampleStatus`). Key transitions:

- `DISCOVERED` -> `COMPILABLE` or `COMPILE_FAILED`
- `COMPILABLE` -> `VERIFIED` or `RUNTIME_FAILED`
- `VERIFIED` -> `MD_UPDATED`
- `MD_UPDATED` -> `FINAL_REVIEW_PASSED` or `FINAL_REVIEW_FAILED`
- `FINAL_REVIEW_PASSED` -> `COMMITTED`

## Phases

### Phase A: Discovery and Extraction

**Implementation**:
- `src/services/discovery_service.py`
- Orchestrator method: `_run_discovery_phase`

**What happens**:

1. Find markdown files based on family config (`content_roots` + patterns) or explicit directory scan.
2. Extract inline code fences that match configured fence patterns.
3. Extract gist references (shortcodes or script tags) if enabled.
4. Normalize language tags (optionally) and filter snippets that do not look like real code.
5. Save `ExampleRecord` rows into SQLite.

### Phase B: Compilation Verification and Fix Loop

**Implementation**:
- `src/services/compilation_service.py`
- Orchestrator method: `_run_compilation_phase`

**What happens**:

1. For each `DISCOVERED` example, generate a temporary .NET project.
2. Wrap snippets into a compilable `Program` structure if needed.
3. Infer missing `using` statements from family defaults and known API maps.
4. Run `dotnet restore` and `dotnet build`.
5. If compilation fails and LLM fixes are enabled, create an LLM fix prompt and retry.
6. Save `CompileAttempt` artifacts and update DB status.

### Phase C: Runtime Verification and Fix Loop

**Implementation**:
- `src/services/runtime_service.py`
- Orchestrator method: `_run_runtime_phase`

**What happens**:

1. For each `COMPILABLE` example, create a temporary .NET project.
2. Copy required sample files into the workspace.
3. Run the compiled program with a timeout.
4. If runtime fails and LLM fixes are enabled, attempt to fix and retry.
5. Save `RuntimeAttempt` artifacts and update DB status.

### Phase D: Markdown Update

**Implementation**:
- `src/services/markdown_service.py`
- Orchestrator method: `_run_markdown_update_phase`

**What happens**:

1. For each markdown file touched by verified examples, locate the relevant fences.
2. Replace inline snippets with `verified_code` (or update gist references depending on mode).
3. Save diffs as artifacts and record `MarkdownEdit` rows.
4. Enforce write guards (see [safety.md](../safety/safety.md)).

### Phase E: Final LLM Review

**Implementation**:
- Orchestrator method: `_run_final_review_phase`
- Contracts: `src/services/llm_contracts.py`

**What happens**:

1. Optionally review updated markdown (often only LLM-fixed examples).
2. Record review results and issues in the DB.
3. Optionally fail the run on critical issues depending on config.

### Phase F: Finalization

**Implementation**:
- Orchestrator method: `_run_finalization_phase`
- Telemetry: `src/core/telemetry.py` and `src/services/telemetry_service.py`

**What happens**:

1. Export run telemetry.
2. Optionally commit changes (git integration is configurable).
3. Mark the DB run complete.

## Data Flow (High Level)

```
Markdown content -> DiscoveryService -> SQLite (examples)
SQLite (examples) -> CompilationService -> SQLite (attempts, status)
SQLite (compilable) -> RuntimeService + test data -> SQLite (attempts, status)
SQLite (verified) -> MarkdownUpdateService -> markdown files + diff artifacts
Updated markdown -> Final review -> SQLite (review results)
Run -> Telemetry export + optional git commit
```

## Entry Points

- **CLI** (`src/cli/main.py`): Command-line interface for running pipeline phases and operational commands.
- **MCP Server** (`src/mcp_tools/server.py`): JSON-RPC server for remote tool execution.
- **HTTP API** (`src/http_server.py`): FastAPI wrapper over MCP tools.

See [entrypoints.md](entrypoints.md) for full command reference.

## Configuration

Configuration is split into:

- **Global Configuration** (`config/global.json`): Defines LLM settings, markdown write guards, vector DB, drift control, telemetry, and backfill settings.
- **Family Configuration** (`config/families/*.json`): Specifies content discovery, build and NuGet settings, code defaults, runtime validation rules, and external resources.

See [configuration.md](../reference/configuration.md) for full reference.

## Known Gaps

For current known issues and limitations, see [known-gaps.md](../assessments/known-gaps.md).
