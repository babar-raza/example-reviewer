## Summary
<!-- What does this MR change and why? -->


## KB Changes (complete if any `config/families/*_review_hints.json` or `*_behavioral_patterns.json` files are modified)

- [ ] `python scripts/validate_kb.py --all` runs clean locally
- [ ] New/changed patterns tested against real code samples (positive AND negative cases)
- [ ] Patterns with `severity: "error"` or `"critical"` have a second reviewer assigned
- [ ] `docs/development/family-kb.md` updated if a new family KB was added
- [ ] Structural test added or existing tests still pass


## Risky Change Checklist

**Check which risky change categories apply to this MR** (see [CONTRIBUTING.md](../../CONTRIBUTING.md)):

- [ ] Pipeline phase logic (`src/pipeline/orchestrator.py`, phase A–F methods)
- [ ] Safety gate change (`path_guard.py`, `provenance_guard.py`, markdown write guard)
- [ ] LLM routing/fallback (`llm_service.py`, `circuit_breaker.py`)
- [ ] KB pattern/hint change (`config/families/*_behavioral_patterns.json` or `*_review_hints.json`)
- [ ] Config schema change (`src/core/config.py`, `config/global.json`)
- [ ] Benchmark-affecting change (could alter any family's compile/runtime/review outcomes)

**If any box is checked, confirm the following before merge:**

- [ ] Test added or updated covering the changed path
- [ ] `pytest tests/ -v --timeout=30` passes locally with no new failures
- [ ] If benchmark-affecting: `.benchmarks/baselines/<family>_baseline.json` updated **or** deferral documented below
- [ ] If safety gate change: second reviewer assigned

**Baseline impact statement** *(required if "benchmark-affecting" is checked)*:
<!-- Describe how this change affects or does not affect the family accuracy rates in evals/ -->


## Test Plan
<!-- How was this tested? -->


## Documentation Impact

- [ ] No documentation changes needed
- [ ] Docs updated — `python scripts/validation/check_doc_links.py` passes locally
- [ ] New doc file added to `docs/index.md` navigation
- [ ] Cross-references to moved/renamed files updated

## Checklist

- [ ] CI passes
- [ ] Documentation updated if behaviour changed
