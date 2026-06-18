# Safety and Write Guards

The pipeline is designed to prevent accidental or adversarial changes to test fixtures and to prevent silent modifications of documentation without explicit authorization.

## Markdown Write Guard

**Implementation**: `src/services/markdown_service.py` (`MarkdownUpdateService`)

By default, markdown writes are blocked.

To allow markdown updates, you must explicitly enable writing by either:

1. Setting `config/global.json` -> `markdown_write.allow_markdown_write` to `true`, or
2. Passing `--allow-md-write` to the CLI for `md-update` or `run`

If writing is not enabled and `dry_run` is `false`, the service raises `MarkdownWriteGuardError`.

## Read-Only Test Paths

The system treats the following path prefixes as strictly read-only:

- `test-data/`
- `test-examples/`
- `test-reference/`

Attempting to write to these locations raises `ReadOnlyPathError`.

**Note**: `test-content/` is explicitly **not** read-only. The pipeline is allowed to update it (when markdown writes are enabled) because it is meant to be the mutable test content set.

## Drift Controls

Two anti-drift defenses exist:

1. **Embedding Drift Threshold Check** (`drift.threshold`)
2. **Semantic Intent Review** (`final_review`) for LLM-fixed examples

These controls reduce the chance that the pipeline introduces major functional changes that merely satisfy compilation.

## Operational Guardrails (Recommended)

These are not enforced by the code in this archive but are recommended for operators:

- Always run `--dry-run` first for a new family
- Limit `--max-examples` during early validation
- Keep a clean git working tree before `md-update` and `commit`
- Persist artifacts (`artifacts/`) for failed runs so the fix loop can be audited