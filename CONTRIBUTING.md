# Contributing to Example Reviewer

## Getting Started

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --timeout=30
python scripts/validate_kb.py --all
```

## Risky Change Categories

The following change types require additional evidence before merge.
They are "risky" because they can silently affect pipeline accuracy or
safety without triggering compilation or test failures.

| Category | Files / Paths | Evidence Required |
|----------|--------------|-------------------|
| Pipeline phase logic | `src/pipeline/orchestrator.py`, phase A–F methods | Test covering the changed phase path; no regression in affected family stats |
| Safety gates | `src/core/path_guard.py`, `src/core/provenance_guard.py`, write guard in `src/services/markdown_service.py` | Tests for both allow and deny paths; see `tests/test_path_guard.py` and `tests/test_provenance_guard.py` |
| LLM routing/fallback | `src/services/llm_service.py`, `src/services/circuit_breaker.py` | Fallback scenario test (see `tests/test_circuit_breaker_scenarios.py` and `tests/test_degraded_mode.py`) |
| KB pattern changes | `config/families/*_behavioral_patterns.json` | Positive + negative code sample tests per changed pattern |
| KB hint changes | `config/families/*_review_hints.json` | `python scripts/validate_kb.py --all` passes |
| Config schema | `src/core/config.py`, `config/global.json` fields | `tests/test_config_loading.py` updated |
| Benchmark-affecting | Any change that could alter compile/runtime outcomes for any family | Updated `.benchmarks/baselines/<family>_baseline.json` **or** explicit deferral rationale in MR |

Use the MR template section "Risky Change Checklist" to certify compliance.

## Benchmark Baseline Policy

When you change pipeline logic that could affect a family's verification rate:

1. Run the affected family through the pipeline on production data
2. Execute `python scripts/evals/generate_baseline.py --family <name> --db-path <path>`
3. Commit the updated `.benchmarks/baselines/<family>_baseline.json`
4. Update `evals/family_accuracy_report.json` if the rate changed meaningfully

**If you cannot run production data** (dev environment without DB sync):
- Document "baseline update deferred — no prod DB access" in the MR body
- Apply the `pending-baseline-update` label
- Create a follow-up issue to refresh the baseline

The CI `eval-baseline-check` job warns (but does not block) when baselines are
older than 90 days. This will surface staleness without gate-blocking work.

## Adding a New Family

1. Add `config/families/<family>.json` with the family configuration
2. Run `python scripts/validate_kb.py --all` to confirm schema validity
3. If adding KB files: follow [docs/development/family-kb.md](docs/development/family-kb.md) governance
4. Add the family to `evals/family_accuracy_report.json` (even if rate is 0%)
5. Generate a baseline: `python scripts/evals/generate_baseline.py --family <name>`
6. Add a row to [docs/assessments/accuracy-audit.md](docs/assessments/accuracy-audit.md)

## Adding KB Patterns or Hints

KB files (`*_behavioral_patterns.json`, `*_review_hints.json`) require:
- `python scripts/validate_kb.py --all` passes locally
- Positive test (code that SHOULD trigger the pattern) **and** negative test
  (code that should NOT trigger) — add to `tests/test_words_fixes.py` or
  create `tests/test_<family>_fixes.py`
- For patterns with `"severity": "error"` or `"critical"`: second reviewer
  required (see CODEOWNERS)
- See [docs/development/family-kb.md](docs/development/family-kb.md) for the full governance process

## Running Tests

```bash
# Full suite (excludes integration and runtime)
PYTHONPATH="..." python -m pytest tests/ -v --timeout=30 -m "not integration and not runtime"

# Fallback/circuit-breaker tests only
python -m pytest -m fallback -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# KB validation
python scripts/validate_kb.py --all
```

## Code Style

- Black for formatting (`black src/ tests/`)
- flake8 for linting (`flake8 src/ tests/`)
- No type: ignore comments without explanation

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(family)`: new family or capability
- `fix(llm)`: bug fix in a specific subsystem
- `test(kb)`: test additions
- `docs(readme)`: documentation only
- `chore(ci)`: CI/tooling changes

## What Not to Change Without Discussion

- `src/core/path_guard.py` — path traversal protection; any weakening requires security review
- `src/core/provenance_guard.py` — source-file provenance; changes must preserve auditability
- `src/pipeline/orchestrator.py` phase gate ordering — reordering phases can silently corrupt output
