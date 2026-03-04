# Example Reviewer — Internal Announcement

## What It Is

**Example Reviewer** is an automated pipeline for validating, fixing, and updating C# code examples embedded in our Aspose product documentation (blog posts, docs, knowledge base articles). It is currently in production use for Aspose.ZIP and Aspose.Words, with Aspose.BarCode and Aspose.OCR in early stages.

It runs locally on Windows, uses Python + SQLite + the .NET SDK, and can be driven from the command line, from an IDE via the MCP protocol, or from an HTTP API.

---

## The Problem

Documentation code examples go stale. The sources of breakage are:

1. **API evolution** — a method is removed or renamed between library versions; the example still references the old name.
2. **LLM-authored drift** — content written or assisted by an LLM can contain plausible-but-wrong API calls (e.g., `archive.SaveAsync()` when that method does not exist in Aspose.ZIP).
3. **Copy-paste errors** — incomplete using directives, wrong constructor signatures, missing namespace qualifications.
4. **Environmental assumptions** — examples that reference files or paths that do not exist in the test environment.

None of these are visible from reading the markdown. They only surface when you actually try to build and run the snippet.

---

## How It Works

The pipeline runs examples through a **Verify → Fix → Verify** loop (VFV) across six sequential phases:

| Phase | What happens |
|---|---|
| **A — Discovery** | Crawls configured content directories, extracts C# code fences and GitHub Gist references from markdown into a SQLite database |
| **B — Compile** | Wraps each snippet into a temporary .NET project, runs `dotnet build`, records success or error |
| **C — Runtime** | Executes each compilable snippet against sample test data in a sandboxed subprocess, records pass or failure |
| **D — Markdown update** | Writes back only the verified (compile + runtime passing) corrected code to the source markdown files |
| **E — LLM review** | A local LLM reviews any LLM-fixed snippet to confirm the fix preserved the original intent |
| **F — Finalization** | Exports telemetry, optionally commits and records the run |

When a snippet fails to compile or run, the pipeline applies fixes in two layers:

1. **Deterministic microfixes** (fast, no LLM) — 10 known patterns applied proactively before the first compile attempt. Examples: missing using directives resolved from the assembly catalog, wrong constructor signatures, incorrect enum values, stream disposal patterns, missing output directories.

2. **LLM-based fixes** (local Ollama, code-specialized model) — for errors that don't match a known pattern, a structured prompt is built with the error message, a list of known non-existent APIs for that library, and the correct namespace catalog. The model is given up to 10 attempts with progressively firmer instructions. All inference runs locally; no code or data is sent externally.

After fixing, the pipeline recompiles and reruns to confirm correctness before anything touches the markdown.

---

## Self-Healing and Learning

The pipeline is not static. Several components allow it to improve automatically as it encounters new failures.

### Assembly Reflection Catalog

The authoritative source of valid types, namespaces, constructors, enums, and methods is extracted directly from the NuGet assembly using .NET reflection — not parsed from documentation or markdown. For Aspose.ZIP this is 138 types across 28 namespaces. For Aspose.Words it is 797 types. When a new library version ships, running one script regenerates the catalog:

```bash
python scripts/extract_assembly_catalog.py Aspose.ZIP <version> Aspose.Zip --full
```

This catalog directly feeds both the deterministic fix layer (which using directives to inject, which enum values are valid) and the LLM prompt context (which APIs are real, which are hallucinated).

### Auto-Learn Pattern Engine

After each run, `scripts/auto_learn.py` clusters the remaining failures by error message and code structure, then surfaces patterns that appear more than once. Each discovered pattern is tracked with:

- **Hit count** — how many examples triggered it
- **Success rate** — how often a fix attempt worked
- **Confidence** — whether it has enough signal to promote to the deterministic layer

For Aspose.Words alone, 29 patterns have been identified through auto-learn. Pattern #25 (a CS0117 error requiring a specific LLM prompt formulation) reached 100% success across all 4 of its occurrences and was promoted. Patterns #24 and #27 had 0% success after 36 and 11 uses respectively and were retired rather than wasting further LLM budget.

This means common failure modes compound over time — errors that required a human or LLM the first time are handled deterministically in subsequent runs.

### Intelligent Fixture Resolver

Runtime failures caused by missing sample files are handled by a 5-tier self-healing resolver before they ever reach the LLM:

| Tier | Strategy |
|---|---|
| 1 | Use the file if it already exists in the workspace |
| 2 | Look up the file in the persistent fixture registry (cross-run cache) |
| 3 | Try a reverse alias (e.g., `sample.zip` → `Archive.zip`) |
| 4 | Match by extension and content type hint |
| 5 | Generate a minimal but structurally valid file on demand |

Generators cover 12 file types: `.docx`, `.doc`, `.pdf`, `.html`, `.txt`, `.png`, `.jpg`, `.bmp`, `.csv`, `.xml`, `.rtf`, `.svg`. They use hint-based selection: a file named `Template.docx` gets the blank template; `Tables.docx` gets a table-structured document. Resolved fixtures are written to a persistent registry so future runs skip the resolver entirely for known paths.

### Semantic Drift Prevention

Before any fixed code is written back to markdown, a 4-gate validator runs:

1. **Signature comparison** — checks that types, methods, and namespaces referenced in the fixed code exist in the assembly catalog
2. **Family classification** — confirms the snippet still targets the correct Aspose product (catches examples that drifted into a different library's API)
3. **Embedding similarity** — computes semantic distance between original and fixed code; a score below threshold blocks the write
4. **LLM intent review** (Phase E) — reviews LLM-fixed examples to confirm the original intent was preserved

A validator returning `reject` blocks the markdown write. Drift signals are stored per-run and can be visualized with `python -m src.cli.main drift-trends --family zip --last-n-runs 10`.

---

## Current Results

The numbers below are derived from commits co-authored by `example-reviewer@aspose.net` in the content repository. "Injected to markdown" means the example was verified (compiled + ran against real test data) and the corrected code was written back to the source `.md` file and committed. "Verified only" means the example passed all pipeline gates but was not written back in that particular run (typically a read-only or status-check run).

| Family | Injected to markdown | Markdown files updated | Additionally verified (not yet injected) |
|---|---|---|---|
| Aspose.Slides | 358 | 222 | 200 |
| Aspose.BarCode | 138 | 63 | 5 |
| Aspose.Cells | 98 | 53 | 50 |
| Aspose.Imaging | 94 | 76 | 50 |
| Aspose.Words | 89 | 33 | 13 |
| Aspose.ZIP | 86 | 38 | 27 |
| Aspose.PDF | 79 | 59 | 22 |
| Aspose.PSD | 65 | 48 | 3 |
| Aspose.OCR | 11 | 8 | 11 |
| Aspose.HTML | 11 | 4 | 2 |
| Aspose.Email | 9 | 3 | 6 |
| Aspose.TeX | 0 | 0 | 57 |
| Aspose.CAD | 1 | 1 | 10 |
| Aspose.Medical | 1 | 1 | 1 |
| **Total** | **1,040** | **609** | **457** |

Across all families, **1,040 verified C# examples have been committed back into 609 documentation files**, with a further 457 examples verified in read-only runs. Aspose.TeX has 57 verified examples pending injection. The pipeline has now touched content across 14 Aspose product families.

---

## Key Technical Components

**Assembly catalog** — Type/namespace/constructor/enum/method data extracted from the NuGet assembly via .NET reflection. ZIP: 138 types, 28 NS. Words: 797 types. Drives both deterministic fixes and LLM prompt context. Regenerated per library version with a single script.

**Fixture resolver** — Self-healing 5-tier service ensuring sample files exist before runtime. Supports 12 file types, hint-aware generation, persistent cross-run registry.

**Semantic drift prevention** — 4-gate validator (signature, family, embedding, LLM review) that blocks markdown writes when a fix deviates too far from the original. Runs before every write.

**Auto-learn** — Clusters failures by error message after each run, surfaces recurring patterns, tracks per-pattern success rates, flags patterns for promotion or retirement.

**Dual-DB mode** — A dev database receives all runs including experiments. A production database receives only committed, reviewed runs. Both are SQLite; the separation is optional and configured via a path or environment variable.

**MCP server** — The pipeline exposes all 13 tools over JSON-RPC (stdio), so any MCP-compatible client (Claude Desktop, IDE extensions) can drive the pipeline without using the CLI. An HTTP API wrapper is also available.

---

## What It Does Not Do

- It does not modify markdown without an explicit `--allow-md-write` flag — all runs default to read-only.
- It does not send any code or data to external APIs; the LLM runs fully locally via Ollama.
- It does not validate documentation prose or non-C# code blocks.
- It does not currently run in CI; it is a local developer tool.

---

## Setup

**Prerequisites:** Python 3.8+, .NET SDK 8.0+, [Ollama](https://ollama.com) with a code model (recommended: `qwen2.5-coder`)

```bash
# One-command setup (creates venv, installs deps, verifies prereqs)
python scripts/setup/setup_wizard.py

# Verify
python -m src.cli.main list-families

# Run a smoke test (20 examples, no markdown writes)
python -m src.cli.main --deterministic --seed 12345 --safe-workspace compile-verify --family zip --max-examples 20
```

The `--safe-workspace` flag copies the SQLite database to a temp location before the run, which avoids file locking issues on OneDrive-synced directories (relevant on Windows).

---

## Adding a New Aspose Family

1. Add `config/families/<name>.json` with content roots, NuGet package reference, safe using directives, and test data configuration.
2. Run `scripts/extract_assembly_catalog.py` against the NuGet package to generate the type catalog.
3. Place or generate test data fixtures in `artifacts/backfill/<name>/test-data/`.
4. Run the pipeline with `--max-examples 20` to validate the setup, then scale up.

Most families have active configs today. Families at lower pass rates (OCR, CAD, TeX) need additional fixture coverage or runtime environment setup specific to their dependencies.

---

## Interfaces

- **CLI** (`python -m src.cli.main`) — primary interface for running gates, viewing status, triggering updates
- **MCP server** — stdio JSON-RPC; configure as an MCP server in Claude Desktop or any MCP-compatible host
- **HTTP API** — `uvicorn src.http_server:app --port 18800` for integration into other tooling
