# pipeline-phases.md

This describes the flow in `PipelineOrchestrator.run_full_pipeline()`.

## Inputs

* family string => loads `config/families/<family>.json`
* options: `max_examples`, `skip_runtime`, `skip_llm_fixes`, `dry_run`, `allow_md_write`

## Phase A: Discovery

Implementation: `_run_discovery_phase()` -> `DiscoveryService.discover_family()`

What happens:

* Find Markdown files from `content_roots` + `content_pattern`
* Extract:

  * fenced code blocks
  * gist references (shortcodes/script tags)
* Filter blocks (line count, exclude patterns, require C# indicators)
* Capture context: nearest heading + paragraphs above snippet
* Save `example_records` with status **DISCOVERED**

Outputs: counts of files processed, examples found, errors.

## Phase B: Compilation verify + fix loop

Implementation: `_run_compilation_phase()`

Input set:

* Examples with status **DISCOVERED** (limited by `max_examples`)

Steps per example:

* Create temp workspace `workspace/compile/compile_<example_id>`
* Generate SDK-style project targeting net8.0 with NuGet refs from family config
* Wrap snippet into compilable structure if needed
* Run `dotnet restore` then `dotnet build`

On success:

* set status **COMPILABLE**
* persist `compilable_code`
* optionally store in vector DB (if enabled)

On failure:

* if `skip_llm_fixes`: mark **COMPILE_FAILED**
* else: LLM fix loop up to `llm.max_retries`

  * Build a fix payload with scaffolding hints
  * Load optional API context from `api_reference.cache_path` (truncated)
  * Retrieve similar examples from vector DB (optional)
  * Call `LLMService.fix_code(context_type="compile", ...)`
  * Drift detection: if `drift.enabled` and drift > threshold and `fail_on_exceed`, abort and mark failed
  * Re-compile after applying candidate fix
  * Record attempt + artifacts

Optional “Stage 5.5”:

* If `final_review.enabled` and `only_review_llm_fixed=true`, run `LLMService.final_review()` on successful LLM-fixed compilation to detect intent drift.

## Phase C: Runtime verify + fix loop (optional)

Implementation: `_run_runtime_phase()`

Input set:

* If skipping LLM fixes: **COMPILABLE**
* Otherwise: **COMPILABLE + RUNTIME_FAILED** (retries)

Steps per example:

* Create temp workspace `workspace/runtime/runtime_<example_id>`
* Copy test-data into workspace (plus alias copies) from `test_data.local_path`
* Run `dotnet restore`, `dotnet build`, then `dotnet run` with timeout

On success:

* set status **VERIFIED**
* persist `verified_code`
* optionally add to vector DB

On failure:

* set status **RUNTIME_FAILED**
* if LLM fixes enabled:

  * classify build/restore failures vs runtime failures
  * choose `context_type="compile"` for build failures, `"runtime"` otherwise
  * include `test_data_info` (file listing + aliases) in prompt context
  * record runtime attempts

Backfill hook:

* if test data path is missing and backfill enabled/configured, attempt auto-backfill.

## Phase D: Markdown update

Implementation: `_run_markdown_update_phase()` -> `MarkdownUpdateService`

* For each file with VERIFIED examples, replace:

  * inline fenced blocks using location metadata
  * gist references (depending on mode)
* Always produce diff artifacts
* **Write guard enforced** unless authorized
* Always block test fixture directories

## Phase E: Final review (optional)

Implementation: `_run_final_review_phase()`

* Uses LLM to review changes and store:

  * `review_results`
  * `review_issues`

## Phase F: Finalization

Implementation: `_run_finalization_phase()`

* Complete run record with stats computed from DB
* Export telemetry (optional)
* Git commit (optional)
* Complete telemetry run (best-effort)
