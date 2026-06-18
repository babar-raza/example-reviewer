# Example Reviewer

Example Reviewer is a Python, SQLite, and .NET SDK pipeline for validating C# examples embedded in Markdown content. It discovers snippets and gist references, compiles them against Aspose NuGet packages, runs verified examples where possible, applies deterministic and LLM-assisted fixes, and can write corrected snippets back to the source Markdown after the configured safeguards allow it.

The project is best understood as a **Verify -> Fix -> Verify (VFV)** system for documentation examples. It is already broad enough to run CLI, MCP, HTTP, CI, telemetry, evidence, and family-specific validation workflows, but it still has operational gaps and several features that depend on local content checkouts, generated catalogs, external tools, and LLM endpoints.

## Current Status

| Area | Current state | Evidence |
|------|---------------|----------|
| Core CLI pipeline | Implemented. Commands cover scan, extract, compile, runtime, markdown update, final review, commit, backfill, drift, review queue, and telemetry verification. | `src/cli/main.py`, `src/mcp_tools/tools.py` |
| MCP server | Implemented as JSON-RPC over stdio with 14 documented tools. | `src/mcp_tools/server.py`, `src/mcp_tools/tools.py`, `docs/architecture/mcp.md` |
| HTTP wrapper | Implemented as a FastAPI wrapper over MCP tools. | `src/http_server.py` |
| Family configs | Present for barcode, cad, cells, email, html, imaging, medical, ocr, page, pdf, slides, smoke, tasks, tex, words, and zip. | `config/families/*.json` |
| Accuracy baselines | Present, but the report explicitly marks circular evidence risk for some fallback data. | `evals/family_accuracy_report.json`, `evals/claim_registry.json` |
| Tests and CI | Unit/integration/fallback/eval jobs exist. GitLab CI is authoritative; GitHub Actions is a mirror subset. | `.gitlab-ci.yml`, `.github/workflows/cli_tests.yml`, `tests/` |
| Setup | Mostly scripted, but real runs need local Aspose content roots, generated API catalogs, .NET SDK, and configured LLM keys for LLM paths. | `scripts/setup/`, `.env.example`, `config/global.json` |
| Write safety | Markdown service enforces write authorization, read-only path guards, block matching, and provenance checks. The checked-in `config/global.json` currently sets `markdown_write.allow_markdown_write` to `true`, so operators should review this before non-dry-run commands. | `src/services/markdown_service.py`, `src/core/path_guard.py`, `src/core/provenance_guard.py`, `config/global.json` |

## What Problem It Solves

Aspose documentation and blog content contains many C# examples. SDK and content changes can silently break those examples:

- API methods, enum members, constructors, or namespaces can change.
- Required `using` directives and package references can drift.
- Runtime examples may assume sample files, directories, passwords, or archive contents that are not present.
- Manual validation does not scale across many product families and content roots.

Example Reviewer automates the repeatable part of that work: find examples, compile them, run them when possible, apply safe repairs, collect evidence, and prepare verified changes for review.

## Project Goals

Current goal:

- Provide a repeatable local and CI-friendly pipeline for validating Aspose C# documentation examples.
- Prefer deterministic repair and validation before spending LLM tokens.
- Keep every run auditable through SQLite state, telemetry, artifacts, run fingerprints, and evidence manifests.
- Make Markdown write-back explicit, reviewable, and constrained to verified examples.

Expected direction:

- Grow from a ZIP-primary validation workflow into a multi-family example quality platform.
- Improve production accuracy baselines without relying on circular or README-derived evidence.
- Expand real integration coverage for .NET SDK, content roots, LLM providers, gist access, and telemetry.
- Harden operator workflows for safe batch runs, scheduled queues, and production DB promotion.

Main users are maintainers, release/quality engineers, documentation operators, and agent clients that need to validate or repair code examples before publishing.

## What Has Been Accomplished

- CLI, MCP, and HTTP entry points exist and share the same tool layer.
- The main orchestrator runs discovery, article validation, gist and fixture backfill, compile verification/fixing, runtime verification/fixing, behavioral scanning, Markdown update, optional final review, finalization, auto-learn, and evidence export.
- SQLite state, run scoping, dual-DB promotion, migration files, telemetry, and run artifact exports are implemented.
- Deterministic layers exist for code wrapping, semantic microfixes, family-specific fixes, fixture generation, app-context classification, behavioral scanning, path guards, and drift/signature checks.
- LLM paths exist for compile/runtime repair, final review, prose audit, gist README generation, model routing, fallback, and auto-learn pattern extraction.
- GitLab CI includes validation, security scan, import analysis, tests, fallback tests, integration tests, and eval freshness/claim checks.
- Family accuracy reports and claim registries exist as machine-readable evidence.

## What Remains Unfinished

- Some docs and comments still reference old paths such as `tools/...` or `scripts/auto_learn.py`; current scripts live under `scripts/ops`, `scripts/validation`, and `scripts/patterns`.
- `.env.example` and `config/global.json` use different gist token names in places (`GIST_PUBLISH_TOKEN`, `GITHUB_GIST_TOKEN`), which needs cleanup.
- The checked-in global config enables Markdown writes by default, while safety docs describe the safer blocked-by-default mode.
- `docs/assessments/known-gaps.md` records missing or stale source-module references and config fields that the current parser ignores.
- Real external integration coverage remains limited. Most tests are unit-style or mocked, with narrow integration tests.
- API catalog files are generated locally and are not all committed; commands depending on catalogs may generate or require them during setup.
- Accuracy reports are strong for production-DB-backed families, but `evals/family_accuracy_report.json` marks `circular_evidence_risk: true` and notes fallback sources for families without production runs.

## Architecture and Execution Flow

The original README described phases A-F. The current orchestrator still follows that shape, with additional preflight and post-processing phases around it.

```text
Markdown content / gist refs / example repos
        |
        v
Phase 0    API catalog check/generation and default using validation
Phase A    Discovery and extraction
Phase A.2  Deterministic article validation
Phase A.5  Gist source backfill and fixture prefetch
Phase A.7  Reference .cs file promotion where applicable
Phase B    Compile verification and compile fix loop
Phase C    Runtime verification and runtime fix loop
Phase C.5  Behavioral scan
Phase D    Markdown update or dry-run diff generation
Phase D.5  Optional standalone prose/fence pass
Phase E    Optional final LLM review and optional intent review
Phase F    Telemetry, optional git commit, dual-DB production copy
Phase F.5  Optional auto-learn pattern extraction
Evidence   Run artifacts and run_evidence.json
```

Primary implementation files:

| Layer | Files | Role |
|-------|-------|------|
| CLI | `src/cli/main.py` | Argparse command surface, deterministic flags, safe workspace handling |
| MCP | `src/mcp_tools/server.py`, `src/mcp_tools/tools.py` | JSON-RPC server and structured tool methods |
| HTTP | `src/http_server.py` | FastAPI wrapper over MCP tool calls |
| Orchestration | `src/pipeline/orchestrator.py` | Run lifecycle, phase sequencing, telemetry, finalization |
| Models and DB | `src/core/models.py`, `src/core/database.py`, `migrations/` | Run/example state, SQLite schema, migrations, dual DB |
| Discovery | `src/services/discovery_service.py` | Markdown and gist example discovery |
| Compile/runtime | `src/services/compilation_service.py`, `src/services/runtime_service.py` | .NET project generation, build/run attempts, timeouts |
| Markdown update | `src/services/markdown_service.py`, `src/utils/markdown_parser.py` | Block matching, write guards, diff artifacts, provenance checks |
| Fix strategies | `src/services/semantic_microfixes.py`, `src/services/family_fixes/`, `src/services/learned_patterns_service.py` | Deterministic and learned fix layers |
| Drift and review | `src/services/semantic_signature_service.py`, `src/services/vector_db_service.py`, `src/services/family_drift_validators/`, `src/services/llm_service.py` | Signature, embedding, family, and LLM review controls |
| Backfill and fixtures | `src/services/backfill_service.py`, `src/services/fixture_resolver_service.py`, `src/services/test_data_generator.py` | API catalogs, gist source, examples, and runtime fixture resolution |

## Deterministic vs LLM-Driven Behavior

The pipeline intentionally tries deterministic behavior before LLM behavior.

### Deterministic paths

These paths do not require an LLM:

- Markdown file discovery, fence parsing, language normalization, and content filtering.
- App-context classification and context harness wrapping.
- Default `using` injection from family config and API catalogs.
- Semantic microfixes for allowlisted compiler errors such as missing types, missing variables, placeholder passwords, and safe argument defaults.
- Family-specific fixes under `src/services/family_fixes/`.
- Runtime fixture extraction, alias lookup, registry lookup, extension matching, and deterministic fixture generation.
- Path guards, provenance guards, read-only path enforcement, no-op Markdown replacement, and block-index self-healing.
- Signature and family drift validators where configured.
- Run fingerprints, selection hashes, stable sorting, SQLite state transitions, and most validation scripts.

### LLM-dependent paths

These paths require a configured OpenAI-compatible endpoint or fallback provider:

- Compile fix loop when deterministic fixes cannot resolve compiler errors.
- Runtime fix loop when deterministic runtime fixes cannot resolve failures.
- Final review and optional intent review.
- Optional prose/code alignment audit and prose correction.
- LLM-powered auto-learn pattern extraction.
- Optional gist README generation.

LLM configuration is in `config/global.json` under `llm`, `final_review`, and `model_routing`. The default checked-in config points at `https://llm.professionalize.com/v1` and uses the `litellm_key` environment variable.

### Safeguards

- Deterministic mode sets temperature to `0.0`, enables deterministic mode, and applies a seed when supported by the provider.
- Provider capability detection checks seed support and logs warnings if the provider rejects it.
- LLM output is parsed through contract objects and category-aware validation in `src/services/llm_service.py`.
- Final review can compare original and fixed examples and reject critical semantic drift.
- Signature, family drift, vector similarity, behavioral scans, and provenance checks provide non-LLM validation around write-back.
- Markdown writes are blocked unless `MarkdownUpdateService` receives write authorization, but the checked-in global config currently enables that authorization by default.

Missing safeguards:

- Real end-to-end tests with live LLM and .NET execution are limited.
- The docs/config mismatch around Markdown write defaults should be resolved.
- Operators should not treat LLM-reviewed output as publication-ready without reviewing diffs and evidence.

## Feature Status and Evidence

| Feature | Trigger | Implementation | Status |
|---------|---------|----------------|--------|
| Family discovery | `scan`, `extract`, `run` | `src/services/discovery_service.py`, `config/families/*.json` | Implemented |
| Gist extraction/backfill | Discovery/backfill flows | `src/services/discovery_service.py`, `src/services/backfill_service.py` | Implemented, network-dependent |
| Compile verification | `compile-verify`, `compile-fix`, `run` | `src/services/compilation_service.py`, `src/pipeline/orchestrator.py` | Implemented, requires .NET SDK |
| Runtime verification | `runtime-verify`, `runtime-fix`, `run` | `src/services/runtime_service.py` | Implemented, fixture-dependent |
| Deterministic microfixes | Compile/runtime phases | `src/services/semantic_microfixes.py`, `src/services/family_fixes/` | Implemented and tested |
| Fixture resolver | Runtime phase | `src/services/fixture_resolver_service.py`, `src/services/test_data_generator.py` | Implemented |
| LLM compile/runtime fixing | `compile-fix`, `runtime-fix`, `run` without `--skip-llm` | `src/services/llm_service.py` | Implemented, endpoint-dependent |
| Final review | `final-review`, `run` when LLM available | `src/pipeline/orchestrator.py`, `src/services/llm_contracts.py` | Implemented but disabled by default in `config/global.json` |
| Markdown update | `md-update`, `run` | `src/services/markdown_service.py` | Implemented with write guards |
| Prose audit | `--audit-prose` | `src/pipeline/orchestrator.py`, `src/services/markdown_service.py` | Optional/experimental |
| Auto-learn | Post-run F.5, `scripts/patterns/auto_learn.py` | `src/pipeline/auto_learn_integration.py`, `scripts/patterns/auto_learn.py` | Implemented, LLM path optional |
| Vector DB drift/search | Startup, drift commands, retrieval strategies | `src/services/vector_db_service.py` | Implemented, dependency-heavy |
| Telemetry | Runs and `telemetry-verify` | `src/core/telemetry.py`, `src/services/telemetry_service.py`, `src/http_server.py` | Implemented |
| Evidence manifest | End of pipeline run | `src/pipeline/evidence.py` | Implemented |
| MCP tool surface | MCP server | `src/mcp_tools/server.py`, `src/mcp_tools/tools.py` | Implemented |
| HTTP API | `uvicorn src.http_server:app ...` | `src/http_server.py` | Implemented |
| CI validation | GitLab CI | `.gitlab-ci.yml` | Implemented |

## Setup From Scratch

### Prerequisites

| Tool | Required for | Check |
|------|--------------|-------|
| Python 3.10+ | CLI, services, tests | `python --version` |
| .NET SDK 8.x | Compile/runtime gates and catalog generation | `dotnet --version` |
| Git | Optional commit/fetch workflows | `git --version` |
| Aspose content checkout | Real Markdown scans | `ASPOSE_CONTENT_ROOT` points to local content |
| LLM endpoint/key | LLM fixes, final review, prose audit, LLM auto-learn | `litellm_key` in environment or `.env` |

### Install

```powershell
git clone <repo-url>
cd example-reviewer-gitlab

python -m venv .venv
.\.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

The repo also has a legacy `venv/` convention in older docs. Use the active interpreter you installed into; commands below assume the virtualenv is activated.

### Environment

Create `.env` from `.env.example` and fill only the values you need.

Important variables:

```bash
# Required for LLM-backed paths
litellm_key=sk-your-api-key-or-provider-key

# Required for real content scans unless you pass --content-roots
ASPOSE_CONTENT_ROOT=/path/to/aspose.net/content

# Optional: raises public gist read rate limits
GITHUB_TOKEN=ghp_read_token

# Optional: gist publishing/upload modes
GITHUB_GIST_TOKEN=ghp_token_with_gist_scope
GIST_PUBLISH_TOKEN=ghp_token_with_gist_scope

# Optional: telemetry API verification target
TELEMETRY_API_URL=http://localhost:8765
```

Note: token naming is not fully consistent across `.env.example`, `config/global.json`, and family configs. Check the config path you are using before enabling gist publishing.

### First-Time Setup Helpers

```powershell
# Interactive setup wizard
python scripts/setup/setup_wizard.py

# Generate or refresh one API catalog
python scripts/setup/bootstrap_catalog.py --family zip --package Aspose.Zip --output config/families/zip_api_catalog.json

# Validate generated/bootstrap data for a family
python scripts/setup/validate_bootstrap.py --family zip
```

Catalog generation and backfill may download NuGet packages, clone example repositories, or use local caches. If setup fails because content roots are missing, set `ASPOSE_CONTENT_ROOT` or use `--content-roots` on scoped commands.

## Usage

Prefer deterministic flags and `--safe-workspace` for reproducible local runs, especially in this checkout path under OneDrive.

```powershell
# Show the command surface
python -m src.cli.main --help

# List configured families
python -m src.cli.main --safe-workspace list-families

# Scan a small number of files
python -m src.cli.main --deterministic --seed 12345 --safe-workspace scan --family zip --max-files 5

# Extract examples from configured content roots
python -m src.cli.main --deterministic --seed 12345 --safe-workspace extract --family zip --max-files 5

# Compile a small batch without LLM fixes
python -m src.cli.main --deterministic --seed 12345 --safe-workspace compile-verify --family zip --max-examples 20

# Runtime verification on a small batch
python -m src.cli.main --deterministic --seed 12345 --safe-workspace runtime-verify --family zip --max-examples 10

# Full pipeline without LLM fixes
python -m src.cli.main --deterministic --seed 12345 --safe-workspace run --family zip --max-examples 50 --skip-llm

# Full pipeline dry-run
python -m src.cli.main --deterministic --seed 12345 --safe-workspace run --family zip --max-examples 50 --dry-run

# Dry-run Markdown update
python -m src.cli.main --deterministic --seed 12345 --safe-workspace md-update --family zip --dry-run
```

Only enable real Markdown writes after reviewing config and diffs:

```powershell
python -m src.cli.main --deterministic --seed 12345 --safe-workspace md-update --family zip --allow-md-write
```

Run the full pipeline with commit only when the working tree and write targets are intentional:

```powershell
python -m src.cli.main --deterministic --seed 12345 --safe-workspace run --family zip --max-examples 50 --allow-md-write --commit
```

Useful scoping options:

```powershell
# Override content roots without editing config
python -m src.cli.main --safe-workspace run --family zip --content-roots C:\content\blog\zip C:\content\kb\zip --max-examples 20

# Run against explicit Markdown files
python -m src.cli.main --safe-workspace run --family zip --files C:\content\zip\article.md --max-examples 5

# Pull work from the DB queue
python -m src.cli.main --safe-workspace run --from-queue
```

Operational scripts live under `scripts/ops`. Treat these as maintainer helpers rather than the primary quickstart path; during this README investigation, `run_all_gates.py --help` worked, while some script internals still referenced old `tools/...` paths or passed CLI flags in stale positions.

```powershell
python scripts/ops/run_all_gates.py --help

$env:PYTHONPATH="src"
python scripts/ops/run_e2e_zip.py --help

python scripts/ops/run_with_hard_timeout.py --help
```

Validation scripts live under `scripts/validation`:

```powershell
python scripts/validation/verify_no_md_changes.py --allow-paths specs/,reports/,docs/,plans/
python scripts/validation/verify_determinism.py run1/results_summary.json run2/results_summary.json
python scripts/validation/analyze_cli_imports.py src/cli/main.py
python scripts/validation/check_doc_links.py
```

Auto-learn scripts live under `scripts/patterns`:

```powershell
python scripts/patterns/auto_learn.py --family zip --dry-run
python scripts/patterns/review_patterns.py --family zip
```

## MCP and HTTP API

Start the MCP server:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m src.mcp_tools.server --verbose
```

The MCP tool surface currently includes:

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

Start the HTTP wrapper:

```powershell
uvicorn src.http_server:app --host 0.0.0.0 --port 18800
```

HTTP endpoints include:

- `GET /healthz`
- `GET /api/v1/tools`
- `POST /api/v1/tools/{tool_name}`
- `POST /api/v1/validate-code`

See `docs/architecture/mcp.md` and `docs/reference/api-reference.md` for protocol and API details.

## Testing and Verification

Install dev requirements first:

```powershell
pip install -r requirements-dev.txt
```

Common test commands:

```powershell
# Full unit-style suite
pytest tests/ -v --timeout=120

# CI-like unit subset
pytest tests/ -v --timeout=120 -m "not integration and not runtime" --tb=short

# Focused safety and docs checks
pytest tests/test_path_guard.py tests/test_provenance_guard.py tests/test_doc_validators.py -v

# MCP checks
pytest tests/test_mcp_server.py tests/test_mcp_tool_definitions.py tests/test_mcp_tools.py -v

# Evidence/claim validators
python scripts/evals/validate_eval_claims.py
python scripts/validation/check_evidence_circularity.py
python scripts/validation/check_baseline_coverage.py
python scripts/validation/check_assessment_freshness.py
```

CI notes:

- `.gitlab-ci.yml` is the authoritative CI definition.
- `.github/workflows/cli_tests.yml` is explicitly marked as a deprecated mirror subset.
- GitLab CI runs validation, security scanning, static import analysis, unit tests, fallback tests, integration tests, and eval checks.

## Generated Files, Cache, Logs, and Evidence

These directories are generated or local-operational data and should not be committed unless a specific evidence artifact is intentionally tracked:

| Path | Purpose |
|------|---------|
| `data/` | SQLite DBs and Chroma vector store |
| `workspace/` | Temporary .NET build/run workspaces |
| `artifacts/` | Diffs, run artifacts, fixture registries, evidence manifests |
| `reports/` | Investigation reports, plans, status files, local evidence bundles |
| `.benchmarks/` | Baseline files used by eval reports |
| `.pytest_cache/`, `.mypy_cache/`, `.coverage` | Test/tool caches |
| `.venv/`, `venv/` | Local Python environments |

Per-run evidence is emitted by `src/pipeline/evidence.py` as:

```text
artifacts/<run_id>/run_evidence.json
```

Run summaries and fingerprints are also exported by the orchestrator into run artifact locations. Accuracy and claim evidence live in:

- `evals/family_accuracy_report.json`
- `evals/claim_registry.json`
- `evals/methodology.md`
- `.benchmarks/baselines/`

## Supported Families

Family configs currently present in `config/families/`:

| Family | Config | Baseline status from `evals/family_accuracy_report.json` |
|--------|--------|----------------------------------------------------------|
| barcode | `config/families/barcode.json` | 128 discovered, 105 verified, 82.0%, production DB |
| cad | `config/families/cad.json` | 9 discovered, 7 verified, 77.8%, production DB |
| cells | `config/families/cells.json` | 192 discovered, 112 verified, 58.3%, production DB |
| email | `config/families/email.json` | 19 discovered, 16 verified, 84.2%, production DB |
| html | `config/families/html.json` | 17 discovered, 15 verified, 88.2%, production DB |
| imaging | `config/families/imaging.json` | 221 discovered, 138 verified, 62.4%, production DB |
| medical | `config/families/medical.json` | 88 discovered, 3 verified, 3.4%, production DB, early |
| ocr | `config/families/ocr.json` | 115 discovered, 12 verified, 10.4%, production DB |
| page | `config/families/page.json` | 8 discovered, 1 verified, 12.5%, production DB |
| pdf | `config/families/pdf.json` | 825 discovered, 621 verified, 75.3%, production DB |
| slides | `config/families/slides.json` | 551 discovered, 60 verified, 10.9%, production DB |
| smoke | `config/families/smoke.json` | 0 discovered, 0 verified, fallback README-documented source |
| tasks | `config/families/tasks.json` | 6 discovered, 0 verified, fallback README-documented source |
| tex | `config/families/tex.json` | 45 discovered, 34 verified, 75.6%, production DB |
| words | `config/families/words.json` | 94 discovered, 84 verified, 89.4%, production DB |
| zip | `config/families/zip.json` | 56 discovered, 49 verified, 87.5%, production DB |

The report date is 2026-06-17. Treat the figures as baselines, not guarantees for a fresh checkout. They depend on local content roots, generated catalogs, test data, and the current production DB.

## Known Gaps and Risks

- The current checkout is under OneDrive; CLI commands warn that SQLite WAL mode on OneDrive can cause locking. Use `--safe-workspace`.
- Running `list-families` with the repo virtualenv succeeded during this README investigation, but initialized DB/vector services and emitted Chroma telemetry errors. The command still returned success.
- Running the CLI with the ambient system `python` failed because dependencies such as `pydantic` were not installed. Use the project virtualenv or install requirements.
- `docs/assessments/known-gaps.md` lists missing/stale source-module references and ignored config fields.
- `config/global.json` currently enables `markdown_write.allow_markdown_write`; confirm this setting before non-dry-run operations.
- Gist token naming is inconsistent across `.env.example` and config files.
- Some ops scripts need cleanup before they are reliable copy/paste workflows. `scripts/ops/run_all_gates.py` still has stale command construction for top-level CLI flags, and `scripts/ops/run_e2e_zip.py` needs `PYTHONPATH=src` plus stale provisioning path cleanup.
- Some older reports contain stale status and mojibake; prefer current source, configs, CI, and eval files over old sprint reports.
- Full live verification can be expensive or environment-dependent because it may need .NET restore/build, NuGet downloads, content roots, test data, network access, and LLM endpoints.

## Recommended Next Steps

1. Normalize Markdown write defaults so docs, config, and operator expectations agree.
2. Fix `.env.example` and config token naming for gist read versus gist publish paths.
3. Replace stale `tools/...` references in docs/agent instructions with `scripts/ops/...` and `scripts/validation/...`.
4. Fix ops script command construction so `scripts/ops/run_all_gates.py` and `scripts/ops/run_e2e_zip.py` are safe copy/paste workflows again.
5. Add or document a lightweight smoke dataset that exercises scan -> compile -> runtime without external content roots.
6. Add live integration test instructions for .NET SDK, NuGet, LLM endpoint, telemetry API, and gist access.
7. Reduce circular evidence risk for `smoke` and `tasks` baselines by generating production-DB-backed runs or marking them explicitly as no-baseline.
8. Add a cleanup command or runbook for `workspace/`, `artifacts/`, `data/chroma`, and stale local DBs.

## Maintainer Notes

- Keep deterministic fixes idempotent. Applying them twice should produce the same output as applying them once.
- Keep run selection stable. Sort file lists and top-N selections deterministically.
- Use `sys.executable` in subprocess helpers instead of hardcoded Python paths.
- Do not bypass write guards, drift checks, provenance checks, or final review to make a run pass.
- Do not commit generated DBs, workspaces, caches, reports, local credentials, or API keys.
- Prefer `python -m src.cli.main ...` as the primary command form. `python -m cli ...` exists as a compatibility wrapper.

## Documentation Map

| Document | Purpose |
|----------|---------|
| `docs/index.md` | Documentation index |
| `docs/architecture/overview.md` | Pipeline phases, entities, and data flow |
| `docs/architecture/architecture.md` | Detailed system design and DB schema |
| `docs/architecture/entrypoints.md` | CLI and MCP entry points |
| `docs/architecture/mcp.md` | MCP protocol and tool surface |
| `docs/architecture/llm-code-fixing-flow.md` | LLM fix loop internals |
| `docs/reference/configuration.md` | Global and family config reference |
| `docs/reference/api-reference.md` | HTTP API reference |
| `docs/reference/local-telemetry-api.md` | Local telemetry API schema |
| `docs/operations/runbook.md` | Operations runbook |
| `docs/safety/safety.md` | Safety and write guards |
| `docs/development/testing-guide.md` | Test guidance |
| `docs/development/development-guide.md` | Development guide |
| `docs/development/family-kb.md` | Family KB governance |
| `docs/assessments/known-gaps.md` | Known gaps and limitations |
| `docs/assessments/accuracy-audit.md` | Baseline accuracy audit |

## Quick Claim-to-Evidence Table

| Claim | Evidence |
|-------|----------|
| The CLI exposes the documented command set. | `src/cli/main.py`; verified with `python -m src.cli.main --help` |
| MCP exposes 14 tools. | `docs/architecture/mcp.md`, `src/mcp_tools/tools.py` |
| HTTP wrapper delegates to MCP tools. | `src/http_server.py` |
| The orchestrator includes phases beyond the older A-F diagram. | `src/pipeline/orchestrator.py` |
| Deterministic microfixes exist. | `src/services/semantic_microfixes.py`, `tests/test_semantic_microfixes.py`, `tests/test_quick_fixes_transformers.py` |
| Fixture resolver uses a 5-tier chain. | `src/services/fixture_resolver_service.py`, `tests/test_fixture_resolver_service.py` |
| Markdown writes are guarded by service and path/provenance checks. | `src/services/markdown_service.py`, `src/core/path_guard.py`, `src/core/provenance_guard.py` |
| GitLab CI is authoritative. | `.gitlab-ci.yml`, `.github/workflows/cli_tests.yml` |
| Accuracy figures come from eval report, with circular evidence risk noted. | `evals/family_accuracy_report.json`, `evals/claim_registry.json` |
