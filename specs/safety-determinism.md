# safety-determinism.md

## Write guards

Implementation: `src/services/markdown_service.py`

Markdown write authorization:

* default is blocked
* enable with `global.json -> markdown_write.allow_markdown_write=true` or CLI `--allow-md-write`

Read-only prefixes (always blocked):

* `test-data/`
* `test-examples/`
* `test-reference/`

## Auditability

* compile/runtime attempts stored in DB + artifacts
* markdown diffs stored and linked via `markdown_edits`

## Drift controls

* Drift score computed during LLM fixes
* Config: `global.json -> drift.enabled`, `drift.threshold`, `drift.fail_on_exceed`
* Exceeding threshold can abort fix loop and mark failure

Final review gate (optional):

* `global.json -> final_review.*`
* Can detect intent drift and reject fixes above confidence threshold

Vector DB drift filtering:

* rejects high-drift examples from being stored
* separate collections for original vs fixed examples
* CLI supports cleaning high-drift items

## Determinism knobs

* LLM temperature (`llm.temperature`) is the primary knob
* Discovery list is sorted; within file block ordering is stable
* Some DB queries order by `created_at` (insertion time), which is stable if discovery order is stable
* Vector DB results depend on embedding model and Chroma versions