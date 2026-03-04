# Example Reviewer

Automated pipeline that extracts C# code examples from markdown content, compiles
and runs them against real NuGet packages and samples, auto-fixes failures, and commits verified
corrections back to the source files.

---

## Table of Contents

1. [What Problem It Solves](#1-what-problem-it-solves)
2. [How It Solves the Problem](#2-how-it-solves-the-problem)
3. [Major Components](#3-major-components)
4. [How Components Communicate](#4-how-components-communicate)
5. [End-to-End Workflow](#5-end-to-end-workflow)
6. [Setup From Scratch](#6-setup-from-scratch)
7. [CLI Reference](#7-cli-reference)
8. [Advanced Usage](#8-advanced-usage)
9. [Supported Families](#9-supported-families)
10. [Documentation Map](#10-documentation-map)

---

## 1. What Problem It Solves

Aspose ships hundreds of C# code examples embedded in markdown blog posts, knowledge-base
articles, and product documentation. As the SDK evolves, those examples silently break:

- API methods are renamed or removed
- Required `using` directives change
- Constructor signatures change between versions
- Runtime dependencies (test files, directories) are assumed but not verified

There is no automated way to catch these regressions at scale. A developer would need to
manually copy each snippet into a project, compile it, run it, fix errors, and paste the
corrected version back — for hundreds of files across a dozen product families.

**Example Reviewer automates this entire workflow end-to-end.**

---

## 2. How It Solves the Problem

The pipeline uses a **Verify → Fix → Verify (VFV)** loop:

```
Markdown files
      │
      ▼
  [Extract]  ─── find all fenced C# blocks and GitHub gists
      │
      ▼
  [Compile]  ─── wrap in Main(), run dotnet build
      │
      ├─ OK ──────────────────────────────────────────────┐
      │                                                    │
      └─ FAIL ──► [Deterministic Fix] ──► [LLM Fix] ──►  │
                   (10+ patterns,          (OpenAI-        │
                   no LLM cost)            compatible)     │
                                                           ▼
                                                       [Runtime]  ─── execute binary
                                                           │
                                                           ├─ OK ──────────────────┐
                                                           │                       │
                                                           └─ FAIL ──► [LLM Fix] ─┤
                                                                                   │
                                                                                   ▼
                                                                           [Final Review]
                                                                     (LLM semantic drift check)
                                                                                   │
                                                                                   ▼
                                                                              [Git Commit]
                                                                      update markdown + commit
```

**Key design choices:**

- Deterministic fixes (stream disposal, missing directives, enum corrections, etc.)
  are applied **first and for free** — no LLM token cost.
- The LLM is called only for errors that the deterministic layer cannot resolve.
- A final LLM review validates that fixes did not change the example's intent (semantic drift).
- All state is stored in SQLite so runs are resumable and auditable.

---

## 3. Major Components

| Layer | Component | Location | Purpose |
|-------|-----------|----------|---------|
| **Entry points** | CLI | `src/cli/main.py` | `argparse`-based interface for all commands |
| | MCP Server | `src/mcp_tools/server.py` | JSON-RPC 2.0 over stdio for Claude Desktop / agents |
| | MCP Tools | `src/mcp_tools/tools.py` | 13 pipeline tools surfaced via MCP |
| **Orchestration** | PipelineOrchestrator | `src/pipeline/orchestrator.py` | Coordinates phases A–F, manages state machine |
| **Core services** | DiscoveryService | `src/services/discovery_service.py` | Scans markdown, extracts code blocks and gists |
| | CompilationService | `src/services/compilation_service.py` | Wraps code in `Main()`, calls `dotnet build` |
| | RuntimeService | `src/services/runtime_service.py` | Executes compiled binary, captures output |
| | LLMService | `src/services/llm_service.py` | OpenAI-compatible LLM calls with `instructor` |
| | MarkdownService | `src/services/markdown_service.py` | Rewrites code blocks in source markdown |
| | SemanticMicrofixes | `src/services/semantic_microfixes.py` | 10+ deterministic C# fix patterns |
| **Support services** | APICatalogService | `src/services/api_catalog_service.py` | Type/method lookup from assembly reflection |
| | FixtureResolverService | `src/services/fixture_resolver_service.py` | Self-healing test data generation (5-tier) |
| | SemanticSignatureService | `src/services/semantic_signature_service.py` | API-level fingerprinting for drift detection |
| | VectorDBService | `src/services/vector_db_service.py` | ChromaDB semantic similarity for drift scoring |
| | LearnedPatternsService | `src/services/learned_patterns_service.py` | Auto-extracted patterns from past fix history |
| | BackfillService | `src/services/backfill_service.py` | Downloads test data, gists, API catalogs |
| | ContextHarnessService | `src/services/context_harness_service.py` | Smart code wrapping (partial snippets, ASP.NET) |
| **Config** | Global config | `config/global.json` | LLM, database, drift, telemetry settings |
| | Family configs | `config/families/<family>.json` | Per-product content roots, NuGet, test data |
| | API catalogs | `config/families/<family>_api_catalog.json` | 137–2700 types reflected from the DLL |
| **Infrastructure** | Database | `src/core/database.py` | SQLite with WAL mode; 17 tables |
| | .NET build host | `test-examples/` | C# project that compiles and runs extracted code |
| | Telemetry | `src/core/telemetry.py` | Event emission, run metrics, HTTP export |

---

## 4. How Components Communicate

```
User / Desktop
       │
       ├─── CLI (argparse)             src/cli/main.py
       │         │
       └─── MCP Client (JSON-RPC 2.0)  src/mcp_tools/server.py
                 │  (stdio, one message per line)
                 │
                 ▼
         ExampleReviewerTools           src/mcp_tools/tools.py
                 │
                 ▼
         PipelineOrchestrator           src/pipeline/orchestrator.py
                 │
        ┌────────┼────────────────────────────────┐
        ▼        ▼                                 ▼
  DiscoverySvc  CompilationSvc              RuntimeSvc
                LLMService                  MarkdownSvc
                SemanticMicrofixes          FixtureResolver
                APICatalogService           SemanticSignature
                LearnedPatternsSvc          VectorDBService
                        │
                        ├── subprocess: dotnet build / dotnet run
                        ├── subprocess: git (via GitPython)
                        └── SQLite:     src/core/database.py
```

**Data flow summary:**

1. CLI / MCP receives command → instantiates `ExampleReviewerTools`
2. Tools call `PipelineOrchestrator` methods (one per phase)
3. Orchestrator calls services; each service has a single responsibility
4. Services write intermediate state to SQLite; orchestrator reads it to decide next action
5. After a verified commit, the run record is copied to the production DB (if configured)

---

## 5. End-to-End Workflow

### Phase A — Discovery

- Scan `content_roots` directories in the family config for `.md` files
- Find every fenced ` ```csharp ``` ` block
- Detect GitHub gist links and fetch their raw content
- Store each code block as an `ExampleRecord` in SQLite with status `DISCOVERED`

### Phase B — Compile

For each discovered example:

1. Classify the code context (console app, library snippet, ASP.NET minimal)
2. Wrap in a `Main()` harness appropriate for the context type
3. **Apply deterministic microfixes proactively** (stream disposal, using directives, enum names)
4. Run `dotnet build`
5. If build fails → apply LLM fix loop (up to `max_llm_retries`)
   - LLM receives: original code + error messages + API catalog context for the relevant types
   - Apply suggested fix, re-compile, repeat
6. Record status `COMPILED` or `COMPILE_FAILED`

### Phase C — Runtime

For each compiled example:

1. **Fixture resolver**: scan code for file string literals, resolve via 5-tier chain
   (existing → fixture registry → extension alias → generate on-the-fly)
2. Execute compiled binary with a timeout
3. If runtime failure → LLM fix loop
4. Record status `VERIFIED` or `RUNTIME_FAILED`

### Phase D — Markdown Update

For each `VERIFIED` example:

- Locate the code block in the source markdown file (by line number or content hash)
- Replace with the verified (possibly fixed) code
- Write updated markdown to disk (requires `--allow-md-write`)
- Record the edit in `markdown_edits` table

### Phase E — Final Review

For every example that was touched by the LLM:

- Send original code, final code, and diff to LLM
- LLM scores semantic fidelity and checks for API drift
- 4-gate validation: signature check → family type check → embedding similarity → LLM verdict
- Status becomes `FINAL_REVIEW_PASSED` or `FINAL_REVIEW_FAILED`

### Phase F — Finalization

- Git commit all modified markdown files with a structured commit message
- Emit run telemetry to local HTTP API (if configured)
- Copy run record to production DB (if dual-DB mode is enabled)

---

## 6. Setup From Scratch

### 6.1 Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Python | 3.10 | `python --version` |
| .NET SDK | 8.0 | `dotnet --version` |
| Git | any | `git --version` |
| LLM endpoint | — | OpenAI-compatible API |

### 6.2 Installation

```bash
git clone <repo-url>
cd example-reviewer

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Linux / macOS

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional — needed for tests

# Run the setup wizard (handles dotnet restore, catalog generation, and test-data scaffolding)
python scripts/setup/setup_wizard.py
```

> `dotnet restore` for the .NET build project is handled automatically by the setup wizard.
> To run it manually: `dotnet restore test-examples/AsposeZipValidator.csproj`

### 6.3 Environment Variables

Create a `.env` file in the repo root **before** running the setup wizard (loaded automatically
at startup):

```bash
# Required: API key for your LLM provider (OpenAI-compatible)
litellm_key=sk-your-api-key-here

# Optional: GitHub token for higher gist rate limits (60 -> 5000 req/hr)
GITHUB_TOKEN=ghp_read_token

# Optional: telemetry HTTP endpoint
TELEMETRY_API_URL=http://localhost:8765
```

### 6.4 Global Configuration

Edit `config/global.json`:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-oss",
    "base_url": "https://your-llm-endpoint/v1",
    "api_key_env_var": "litellm_key",
    "temperature": 0.2,
    "max_retries": 2,
    "timeout_seconds": 120
  },
  "database": {
    "path": "./data/example_reviewer.db"
  }
}
```

### 6.5 Family Configuration

Each Aspose product has its own `config/families/<family>.json`. The key fields:

```jsonc
{
  "family": "zip",
  "display_name": "Aspose.ZIP",
  "content_roots": [
    "C:/content/aspose.net/blog",
    "C:/content/aspose.net/kb"
  ],
  "nuget_config": {
    "package": "Aspose.Zip",
    "version": "25.1.0"
  },
  "api_catalog": {
    "path": "config/families/zip_api_catalog.json"
  },
  "runtime_validation": {
    "required_files": ["sample.zip", "alice29.txt"],
    "timeout_seconds": 30
  }
}
```

### 6.6 Generate API Catalogs (required — not bundled in the repo)

> **API catalog files are not committed to the repository.** They are generated
> from the compiled NuGet assembly via .NET reflection and must be created locally
> before the pipeline can run. The setup wizard (step 5) does this automatically.
> If you skipped the wizard or need to regenerate for a specific family, run the
> script directly.

```bash
# Recommended: use the setup wizard (handles all families interactively)
python scripts/setup/setup_wizard.py

# Or generate a single family's catalog manually:
python scripts/setup/extract_assembly_catalog.py \
    Aspose.Zip 25.1.0 Aspose.Zip --full \
    > config/families/zip_api_catalog.json

# For a family where the package name differs from the DLL name (e.g. Slides):
python scripts/setup/extract_assembly_catalog.py \
    Aspose.Slides.NET 25.1.0 Aspose.Slides --dll-name Aspose.Slides --full \
    > config/families/slides_api_catalog.json
```

The script downloads the NuGet package, loads the DLL via .NET reflection, and
dumps the exported type/enum/constructor/method surface as JSON. This takes
30–60 seconds per family on first run (subsequent runs are faster as NuGet caches
the package locally).

Without a catalog, the deterministic fixer cannot resolve missing `using` directives
and the LLM will receive no type context, significantly lowering the fix success rate.

### 6.7 Backfill Test Data

Download sample test files required by runtime validation:

```bash
PYTHONPATH=. python -m src.cli.main backfill --family zip
```

### 6.8 Verify the Setup

```bash
# Run the test suite
pytest tests/ -v --timeout=120

# Run a small discovery scan
PYTHONPATH=. python -m src.cli.main scan --family zip --max-files 5

# Check what the pipeline found
PYTHONPATH=. python -m src.cli.main status --family zip
```

---

## 7. CLI Reference

All commands follow the pattern:
```bash
PYTHONPATH=. python -m src.cli.main <command> [options]
```

### 7.1 Pipeline Commands

| Command | What it does |
|---------|-------------|
| `run` | Run the full pipeline (phases A–F) |
| `scan` | Phase A: locate markdown files in content roots |
| `extract` | Phase A: extract code blocks and gist content |
| `compile-verify` | Phase B: compile without applying fixes |
| `compile-fix` | Phase B: compile with deterministic + LLM fixes |
| `runtime-verify` | Phase C: run compiled code without fixes |
| `runtime-fix` | Phase C: run with LLM fixes for runtime failures |
| `md-update` | Phase D: overwrite markdown with verified code |
| `final-review` | Phase E: LLM semantic-drift review |
| `commit` | Phase F: git commit all verified changes |

### 7.2 Utility Commands

| Command | What it does |
|---------|-------------|
| `status` | Show counts per status for the current run |
| `list-families` | List all configured families |
| `backfill` | Download test data, API catalogs, and gist source |
| `visualize-drift` | Show semantic drift scores for recent examples |
| `drift-trends` | Plot drift score trends over multiple runs |
| `clean-vector-db` | Remove high-drift entries from the vector store |
| `review-queue` | List examples awaiting manual review |
| `telemetry-verify` | Verify the telemetry HTTP API is reachable |

### 7.3 Common Flags

These flags apply to `run` and most phase commands:

```
--family NAME          Required. Which product family to process.
--max-examples N       Cap the number of examples processed in this run.
--content-roots PATH…  Override the content_roots from family config.
--db-path PATH         SQLite database path (default: data/example_reviewer.db).
--workspace-dir PATH   Temp build directory (default: workspace/).
--allow-md-write       Permit overwriting source markdown files.
--dry-run              Preview all changes without writing anything.
--skip-llm             Deterministic fixes only; skip LLM calls entirely.
--safe-workspace       Move DB and workspace to a non-OneDrive path.
--prod-db-path PATH    Enable dual-DB mode; write committed runs here too.
--deterministic        Enable seed-based reproducibility.
--seed N               Random seed for deterministic mode (default: 42).
--verbose / -v         Debug logging.
--json                 Output results as JSON.
```

### 7.4 Example Invocations

```bash
# Full pipeline — 50 examples, allow writing, auto-commit
PYTHONPATH=. python -m src.cli.main run \
    --family zip \
    --max-examples 50 \
    --allow-md-write \
    --commit

# Deterministic fixes only (zero LLM cost)
PYTHONPATH=. python -m src.cli.main run --family zip --skip-llm

# Preview everything without writing
PYTHONPATH=. python -m src.cli.main run --family zip --dry-run

# Override which folders to scan (without editing config)
PYTHONPATH=. python -m src.cli.main scan \
    --family zip \
    --content-roots /path/to/blog /path/to/kb

# Run compile + fix phase in isolation
PYTHONPATH=. python -m src.cli.main compile-fix --family zip

# Run on a safe workspace (avoids OneDrive SQLite locking on Windows)
PYTHONPATH=. python -m src.cli.main run --family zip --safe-workspace
```

---

## 8. Advanced Usage

### 8.1 MCP Server — Drive the Pipeline from Claude Desktop

The entire pipeline is exposed as a **Model Context Protocol (MCP) server**. Any MCP-compatible
client (Claude Desktop, custom agents) can call all 13 pipeline tools without touching the CLI.

**Start the server:**

```bash
# From repo root (activate venv first)
PYTHONPATH=. venv/Scripts/python.exe -m src.mcp_tools.server

# With explicit paths
PYTHONPATH=. venv/Scripts/python.exe -m src.mcp_tools.server \
    --config-dir config/families \
    --db-path data/example_reviewer.db \
    --workspace-dir workspace \
    --verbose
```

**Claude Desktop integration** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "example-reviewer": {
      "command": "C:/path/to/repo/venv/Scripts/python.exe",
      "args": ["-m", "src.mcp_tools.server"],
      "cwd": "C:/path/to/repo",
      "env": { "PYTHONPATH": "." }
    }
  }
}
```

**Available MCP tools:**

| Tool | Equivalent CLI command |
|------|----------------------|
| `scan` | `scan` |
| `extract` | `extract` |
| `compile_verify` | `compile-verify` |
| `compile_fix` | `compile-fix` |
| `runtime_verify` | `runtime-verify` |
| `runtime_fix` | `runtime-fix` |
| `md_update` | `md-update` |
| `final_review` | `final-review` |
| `commit` | `commit` |
| `run_pipeline` | `run` |
| `backfill` | `backfill` |
| `status` | `status` |

See [docs/mcp.md](docs/mcp.md) for the full JSON-RPC protocol reference.

---

### 8.2 Semantic Drift Detection

The pipeline prevents LLM fixes from silently changing an example's meaning using a
4-gate validation system:

1. **Signature gate** — API fingerprints (enum members, method signatures, constructor overloads)
   are compared before and after the fix
2. **Family type gate** — Types must belong to the correct Aspose product namespace
3. **Embedding similarity gate** — ChromaDB cosine similarity scored against the original
4. **LLM review gate** — Final LLM verdict on semantic fidelity

```bash
# View drift scores for recent examples
PYTHONPATH=. python -m src.cli.main visualize-drift --family zip

# View drift trends over multiple runs
PYTHONPATH=. python -m src.cli.main drift-trends --family zip

# Prune high-drift examples from the vector store
PYTHONPATH=. python -m src.cli.main clean-vector-db --family zip --threshold 0.3
```

Configure in `config/global.json`:

```json
{
  "vector_db": { "enabled": true, "drift_tolerance": 0.02 },
  "final_review": {
    "enable_signature_validation": true,
    "reject_critical_enum_changes": true
  }
}
```

---

### 8.3 API Catalog Generation

The deterministic fixer and the LLM context both rely on an **API catalog** — a JSON file
that lists every exported type, enum, constructor, and method signature from the compiled
assembly. This is generated via .NET assembly reflection (not markdown parsing):

```bash
# Basic catalog (types + namespaces only)
python scripts/setup/extract_assembly_catalog.py \
    Aspose.Zip 25.1.0 Aspose.Zip \
    > config/families/zip_api_catalog.json

# Full catalog with enums, constructors, and method signatures
python scripts/setup/extract_assembly_catalog.py \
    Aspose.Words 26.1.0 Aspose.Words \
    --include-enums \
    --include-constructors \
    --include-methods \
    > config/families/words_api_catalog.json
```

The script downloads the NuGet package, loads the DLL into a temporary C# reflector, and
dumps the exported surface as JSON.

---

### 8.4 Dual-Database Mode

By default, every run (including failures and experiments) goes into `data/example_reviewer.db`.
Dual-DB mode adds a **production DB** that receives records only after a successful git commit.

Enable in `config/global.json`:

```json
{
  "database": {
    "path": "./data/example_reviewer.db",
    "production_path": "./data/example_reviewer_prod.db"
  }
}
```

Or per-run via CLI:

```bash
PYTHONPATH=. python -m src.cli.main run \
    --family zip \
    --prod-db-path ./data/example_reviewer_prod.db
```

The production DB contains only committed, verified runs — useful for dashboards and audits.

---

### 8.5 Self-Healing Test Data (Fixture Resolver)

When an example references a test file that doesn't exist, the fixture resolver automatically
provides one using a 5-tier resolution chain:

1. **Existing** — file already present in the test-data directory
2. **Registry** — previously registered alias in `fixture-registry.json`
3. **Reverse alias** — alternate name mapping in the family config
4. **Extension match** — find any file with the right extension
5. **Generate** — create a minimal valid file on-the-fly (`.docx`, `.pdf`, `.png`, `.zip`, etc.)

Configure in the family JSON:

```json
{
  "fixture_resolver": {
    "enabled": true,
    "auto_generate": true
  }
}
```

The resolver runs **proactively** (scanning C# string literals before the first run) and
**reactively** (triggered by a `FileNotFoundException` at runtime).

---

### 8.6 Auto-Learn Pattern Extraction

Successful LLM fixes are clustered and promoted to deterministic patterns automatically.
This makes future runs faster and cheaper.

```bash
# Cluster failures from recent runs and extract patterns
python scripts/auto_learn.py --family zip --min-attempts 5

# Review pending patterns (approve / retire)
python scripts/review_patterns.py --family zip
```

Patterns with a success rate below 10% after 10+ uses are auto-retired.

---

### 8.7 Dry-Run Mode

Preview all changes without writing to disk or calling `git commit`:

```bash
# Full pipeline dry-run
PYTHONPATH=. python -m src.cli.main run --family zip --dry-run

# Inspect what md-update would change
PYTHONPATH=. python -m src.cli.main md-update --family zip --dry-run
```

---

### 8.8 Safe Workspace (OneDrive / WSL)

SQLite's WAL mode is incompatible with OneDrive sync on Windows and with WSL's DrvFS
(`/mnt/c`, `/mnt/d`). Use `--safe-workspace` to move the DB and build directory to a
local path automatically:

```bash
PYTHONPATH=. python -m src.cli.main run --family zip --safe-workspace
```

Windows: moves to `%LOCALAPPDATA%\ExampleReviewer\workspaces\<timestamp>`
Linux/WSL: moves to `~/.cache/example_reviewer/workspaces/<timestamp>`

---

## 9. Supported Families

| Family | Config file | Status |
|--------|------------|--------|
| ZIP | `config/families/zip.json` | Production — 97.7% verified |
| Words | `config/families/words.json` | Production — 93.2% verified |
| PDF | `config/families/pdf.json` | Configured |
| Email | `config/families/email.json` | Configured |
| Cells | `config/families/cells.json` | Configured |
| Slides | `config/families/slides.json` | Configured |
| Barcode | `config/families/barcode.json` | Configured |
| Imaging | `config/families/imaging.json` | Configured |
| OCR | `config/families/ocr.json` | Configured |
| CAD | `config/families/cad.json` | Configured |
| HTML | `config/families/html.json` | Configured |
| Tasks | `config/families/tasks.json` | Configured |
| PSD | `config/families/psd.json` | Configured |
| Medical | `config/families/medical.json` | Configured |
| TeX | `config/families/tex.json` | Configured |

To add a new family: copy any existing family JSON, update `content_roots` and `nuget_config`,
generate the API catalog, and run `backfill`.

---

## 10. Documentation Map

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | Detailed system design, phase controllers, DB schema |
| [docs/configuration.md](docs/configuration.md) | Full reference for global.json and family configs |
| [docs/pipeline.md](docs/pipeline.md) | Deep dive into phases A–F |
| [docs/mcp.md](docs/mcp.md) | MCP server protocol, tool schemas, Claude Desktop setup |
| [docs/entrypoints.md](docs/entrypoints.md) | CLI and MCP entry points reference |
| [docs/operations.md](docs/operations.md) | Day-to-day operations runbook |
| [docs/ops-runbook.md](docs/ops-runbook.md) | Incident response and recovery procedures |
| [docs/testing-guide.md](docs/testing-guide.md) | Unit test patterns and fixture conventions |
| [docs/development-guide.md](docs/development-guide.md) | Contributing guide, code conventions |
| [docs/local-telemetry-api.md](docs/local-telemetry-api.md) | Telemetry event schema (v3.0.0) |
| [docs/llm-code-fixing-flow.md](docs/llm-code-fixing-flow.md) | LLM fix loop internals |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 5-minute getting-started guide |
| [docs/SQLITE_LOCKING.md](docs/SQLITE_LOCKING.md) | SQLite + OneDrive / WSL concurrency guide |
| [docs/HARDENING_NOTES.md](docs/HARDENING_NOTES.md) | Security hardening decisions |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Version history and breaking changes |

Each directory in the repo also contains its own `README.md` with folder-level details.

---

## Running Tests

```bash
# Full test suite
pytest tests/ -v --timeout=120

# Specific module
pytest tests/test_semantic_microfixes.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# MCP protocol compliance
pytest tests/test_mcp_server.py tests/test_mcp_tool_definitions.py -v
```
