# snapshot-health.md

This repo snapshot is not fully self-contained.

* Missing packaging and dependency manifest: no README, no requirements/pyproject.
* Bytecode-only modules exist under `__pycache__` that reference sources not present:

  * `src/patching/` (expected patching sources missing)
  * `src/validation/analysis/` and `src/validation/fixing/`
  * discovery-related cached modules like `gist_service` and `snippet_locator`
* Family config schema drift: some JSON keys are ignored by the parser.
* Windows absolute paths in some `content_roots`.
* No tests directory in snapshot.

---

# Component specs

## components/discovery.md

* Finds markdown files via glob patterns or rglob
* Extracts fenced blocks + gist references
* Filters using line count, exclusion patterns, and C# indicators
* Captures context above snippet (heading + paragraphs)
* Saves `ExampleRecord` rows with DISCOVERED

## components/compilation.md

* Wraps snippet into a compilable Program/Main when needed
* Generates net8.0 csproj with NuGet refs from family config
* Runs `dotnet restore` + `dotnet build`
* Categorizes errors to produce scaffolding hints
* Records compile attempts + artifacts
* Success => COMPILABLE + compilable_code

## components/runtime.md

* Copies test data into workspace, including alias copies
* Runs restore/build/run with configured timeout
* Classifies restore/build errors as build failures during runtime to route to compile-style fixes
* Records runtime attempts + artifacts
* Success => VERIFIED + verified_code

## components/llm.md

* OpenAI-compatible client (OpenAI/Azure/Ollama/proxies)
* Fixes code via `fix_code(context_type=compile|runtime)` using:

  * error logs, scaffolding hints, optional API context, optional similar examples
  * snippet context: heading, paragraph, topic
* Optional final review to detect intent drift

## components/markdown-update.md

* Uses snippet location metadata to find fences and replace code
* Generates unified diffs and stores them
* Enforces write guard and read-only prefixes
* Updates status to MD_UPDATED and records `markdown_edits`

## components/vector-db.md

* Optional Chroma + sentence-transformers embedding store
* Stores examples in `original_examples` and `fixed_examples`
* Rejects high-drift inserts
* Used to retrieve similar examples to guide LLM fixes

## components/telemetry.md

* Phase timing events stored in SQLite (`TelemetryEvent`)
* Run telemetry dual-written to SQLite + optional HTTP API (`TelemetryRun`)
* Export helper writes JSON run summaries and artifact indices

## components/backfill.md

* Optional helper to fetch missing data
* Test data backfill from `example_repo` (requires GitPython)
* API reference backfill into `api_reference.cache_path`
* Best-effort behavior: failures should not crash the main pipeline unless missing data is required
