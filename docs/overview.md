# Overview

The Example Reviewer pipeline is designed to extract, validate, and update code examples embedded in markdown documentation. It ensures that code snippets are compilable, executable, and consistent with their intended functionality.

## Key Features

- **Discovery and Extraction**: Locates and extracts code snippets from markdown files.
- **Compilation and Runtime Verification**: Validates code snippets for compilation and runtime correctness.
- **LLM-Based Fixes**: Uses Large Language Models (LLMs) to fix compilation and runtime errors.
- **Markdown Updates**: Safely updates markdown files with verified code snippets.
- **Telemetry and Artifacts**: Tracks pipeline execution and stores artifacts for debugging and analysis.

## Pipeline Phases

The pipeline consists of the following phases:

1. **Phase A: Discovery and Extraction**
   - Locates markdown files based on family configuration.
   - Extracts inline code fences and gist references.
   - Normalizes language tags and filters snippets.

2. **Phase B: Compilation Verification and Fix Loop**
   - Generates temporary .NET projects for code snippets.
   - Compiles snippets and fixes errors using LLM if enabled.

3. **Phase C: Runtime Verification and Fix Loop**
   - Executes compiled code snippets with sample data.
   - Fixes runtime errors using LLM if enabled.

4. **Phase D: Markdown Update**
   - Updates markdown files with verified code snippets.
   - Enforces write guards to prevent accidental modifications.

5. **Phase E: Final LLM Review**
   - Reviews LLM-fixed code snippets for intent preservation.

6. **Phase F: Finalization**
   - Exports telemetry and optionally commits changes.

## Entry Points

The system provides two primary entry points:

- **CLI**: Command-line interface for running pipeline phases and operational commands.
- **MCP Server**: JSON-RPC server for remote tool execution.

## Configuration

Configuration is split into:

- **Global Configuration**: Defines LLM settings, markdown write guards, vector DB, drift control, telemetry, and backfill settings.
- **Family Configuration**: Specifies content discovery, build and NuGet settings, code defaults, runtime validation rules, and external resources.

## Safety and Write Guards

- **Markdown Write Guard**: Prevents accidental modifications to markdown files unless explicitly enabled.
- **Read-Only Test Paths**: Protects test data and reference files from modifications.
- **Drift Controls**: Ensures LLM fixes do not deviate significantly from the original code.

## Known Gaps

- Missing source files referenced by bytecode caches.
- No root README, packaging, or dependency manifest.
- Config schema mismatches and Windows-specific assumptions.
- Minimal test coverage in the archive.

For more details, refer to the [Known Gaps](known-gaps.md) section.