# data-model.md

## ExampleRecord

Represents one extracted snippet in one Markdown file.

Identity and location

* `example_id`: stable content hash (family + file path + block index + original code)
* `file_path`, `source_type` (inline/gist)
* `location_block_index`, `location_start_line`, `location_end_line`, `location_anchor`

Code

* `original_code`
* `compilable_code`
* `verified_code`

LLM intent-preservation context

* `section_heading`
* `description_context`
* `topic`

## State machine (ExampleStatus)

* DISCOVERED
* COMPILE_FAILED
* COMPILABLE
* RUNTIME_FAILED
* VERIFIED
* MD_UPDATED
* FINAL_REVIEW_PASSED
* FINAL_REVIEW_FAILED
* COMMITTED

Nominal transitions (as encoded in models):

* DISCOVERED -> COMPILABLE or COMPILE_FAILED
* COMPILE_FAILED -> COMPILABLE
* COMPILABLE -> VERIFIED or RUNTIME_FAILED
* RUNTIME_FAILED -> VERIFIED
* VERIFIED -> MD_UPDATED
* MD_UPDATED -> FINAL_REVIEW_PASSED or FINAL_REVIEW_FAILED
* FINAL_REVIEW_PASSED -> COMMITTED

Note: the orchestrator uses a subset; some statuses exist for future hardening.

## Attempts and audit

* `compile_attempts`: compiler logs, input/output code refs, LLM request/response refs, errors/warnings
* `runtime_attempts`: stdout/stderr, exit codes, artifact refs, retrieved example refs, LLM request/response refs
* `markdown_edits`: diff refs and edit type
* `run_records`: run lifecycle, status, counters
* `telemetry_events`: phase timing + other events
* `telemetry_runs`: larger run schema for dual-write to HTTP API + SQLite
* `gist_publications`: tracks gist id changes and URLs

## Drift fields

DB columns include `drift_score` and `drift_similarity` on `example_records` and are updated during LLM fixing.
