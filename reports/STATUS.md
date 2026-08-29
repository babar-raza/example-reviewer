# Sprint Status — Group 9 (Quarterly Score Improvement — Waves 0–4)

> **Investigation override (2026-08-29):** An independent evidence-first production-readiness investigation (`reports/investigation/20260829_124758_production_readiness/`) postdates every entry in this file by 2+ months and found the system NOT_READY, including confirmed Blocker/Critical defects not reflected below. Treat the sprint statuses below as historical record of that quarter's work, not as current system state — see `EXECUTIVE_VERDICT.md` and `FINDINGS_REGISTER.md` in the referenced investigation for the current, evidence-verified status.

> Generated: 2026-04-20
> Plan source: `C:\Users\prora\.claude\plans\iridescent-wibbling-ladybug.md`
> Baseline score: Engineering 52.0 · Ranked 51.0
> Target: 65–72

---

## Task Status (Group 9)

| Task | File(s) | Status | Notes |
|------|---------|--------|-------|
| TC-01 | `scripts/evals/generate_baseline.py` | COMPLETE | 14 baseline files generated |
| TC-02 | `evals/family_accuracy_report.json`, `evals/methodology.md`, `.benchmarks/README.md` | COMPLETE | All 16 families documented |
| TC-03 | `tests/test_circuit_breaker_scenarios.py` | COMPLETE | 27 tests, all pass |
| TC-04 | `tests/test_degraded_mode.py` | COMPLETE | 11 tests, all pass |
| TC-05 | `tests/test_kb_error_handling.py` | COMPLETE | 9 tests, all pass |
| TC-06 | `.gitlab-ci.yml` | COMPLETE | 3 stages: validate/test/eval |
| TC-07 | `scripts/evals/check_eval_freshness.py`, `scripts/evals/validate_eval_claims.py` | COMPLETE | validate exits 0 on all 16 families |
| TC-08 | `docs/accuracy-audit.md`, `evals/claim_registry.json` | COMPLETE | Unverified fraction analyzed |
| TC-09 | `CONTRIBUTING.md`, `CODEOWNERS`, `.gitlab/merge_request_templates/default.md` | COMPLETE | CODEOWNERS extended 6 lines |
| TC-10 | `scripts/validation/check_risky_diff.py` | COMPLETE | warn-only by default |
| TC-11 | `scripts/skills/score_readiness.py`, `scripts/skills/eval_update.py` | COMPLETE | Score readiness: 5 PASS, 1 PARTIAL |

---

## Score Readiness Audit (2026-04-20)

Run: `python scripts/skills/score_readiness.py`

| Dimension | Status | Notes |
|-----------|--------|-------|
| Eval Freshness | PASS | report_date = 2026-04-20 (0 days old) |
| Benchmark Completeness | PARTIAL | 10/13 production families; psd/barcode/ocr have no config files |
| Fallback Test Coverage | PASS | All 3 fallback test files exist and pass |
| Docs-to-Code Alignment | PASS | 16/16 README claims match eval report (0% delta) |
| CI Evidence | PASS | .gitlab-ci.yml with unit-tests, fallback-tests, eval-baseline-check |
| CODEOWNERS Coverage | PASS | evals/, .benchmarks/, orchestrator, path_guard, KB subsystem all covered |

**Overall: PARTIAL** (no FAILs; one PARTIAL due to missing config files for 3 families)

---

## Test Results

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_circuit_breaker_scenarios.py` | 27 | PASS |
| `tests/test_degraded_mode.py` | 11 | PASS |
| `tests/test_kb_error_handling.py` | 9 | PASS |
| All importable tests (excl. pydantic_settings import failures) | 907 | PASS |

Fallback tests run command:
```bash
PYTHONPATH="C:/Users/prora/AppData/Roaming/Python/Python313/site-packages" \
  python -m pytest tests/test_circuit_breaker_scenarios.py tests/test_degraded_mode.py tests/test_kb_error_handling.py -v
```

---

# Sprint Status — Group 8 (Part III + Part IV Verification)

> Generated: 2026-04-07
> Final test run: 114 passed in 1.42s (5 test files)

---

## Task Status

| Task | Owner | Status | Score | Notes |
|------|-------|--------|-------|-------|
| TASK-022 | C-tests | ✅ VERIFIED | — | `validate_kb.py --all` exits 0; CI step added to `cli_tests.yml` |
| TASK-023 | C-tests | ✅ VERIFIED | — | 3 KBLoadError tests pass: propagation, no-cache, scan-example |
| TASK-024 | B-impl | ✅ VERIFIED | — | `config_dir` threaded through full call chain; custom-dir test passes |
| TASK-025 | E-governance | ✅ FILE PLACED | — | `CODEOWNERS` at repo root; GitLab enforcement requires admin action post-push |
| TASK-026 | E-governance | ✅ FILE PLACED | — | `.gitlab/merge_request_templates/` created; UI verification requires push |
| TASK-027 | C-tests | ✅ VERIFIED | — | Auto-discovery test passes on current `config/families/` |
| TASK-028 | C-tests | ✅ VERIFIED | — | pytest 9.0.2 via PYTHONPATH override; 114 tests run |
| TASK-029 | C-tests | ✅ VERIFIED | — | 114 passed across 5 test files |
| TASK-030 | C-tests | ✅ VERIFIED | 4.4/5 avg | `_review_with_instructor` accepts `content_type`+`config_dir`; no TypeError |
| TASK-031 | C-tests | ✅ VERIFIED | 4.4/5 avg | Sentinel found in LLM prompt; absent with default `config_dir` |
| TASK-032 | E-governance | ⚠️ PARTIAL | — | Files committed; push + admin settings are external dependencies |
| FIX-001 | B-impl | ✅ VERIFIED | — | `OpenAI = None` stub; `from src.services.llm_service import LLMService` succeeds |

---

## Self-Review Summary (TASK-030 + TASK-031)

Full scorecard in `reports/agents/C-tests/TASK-030/self_review.md`.

| Dimension | Score |
|-----------|-------|
| Coverage | 4/5 |
| Correctness | 5/5 |
| Evidence | 5/5 |
| Test Quality | 4/5 |
| Maintainability | 4/5 |
| Safety | 5/5 |
| Security | 5/5 |
| Reliability | 4/5 |
| Observability | 4/5 |
| Performance | 5/5 |
| Compatibility | 4/5 |
| Docs/Specs Fidelity | 4/5 |

**Overall: PASS** (all ≥ 4/5)

---

## Known Gaps

### Gap 1: Instructor E2E path not fully captured
TASK-031 covers `_review_with_manual_parsing` sentinel injection. The instructor path (`_review_with_instructor`) E2E config_dir threading is covered by TASK-030 mock assertion only — proves forwarding to `_build_family_review_hints`, but does not capture the final LLM prompt string. Acceptable because `_review_with_instructor` raises `UnboundLocalError` internally (see Gap 2) without a real client, making prompt capture impractical.

### Gap 2: `_instructor_mode` UnboundLocalError (pre-existing bug)
`_review_with_instructor` exception handler at `llm_service.py:2298` references `_instructor_mode` before assignment. This is a pre-existing bug not introduced by Group 8 changes. Hardening ticket exists in `reports/HARDENING_TICKETS/`.

### Gap 3: TASK-032 post-push verification pending
CODEOWNERS and MR templates are present in working tree but GitLab enforcement (branch protection "Require code owner approval") requires admin action after push. Not blockable by code.

### Gap 4: Two-reviewer enforcement requires GitHub/GitLab settings
The CODEOWNERS file is a prerequisite; the enforcement count (2 reviewers for `severity: "error"` patterns) requires `Settings > Repository > Protected branches` to be configured. Documented in `docs/family-kb.md`.

---

## Remaining Work Before Merge

1. **Commit all changes** — all working tree changes are unstaged
2. **Push to GitLab** — triggers CI validation step (TASK-022)
3. **Admin: enable "Require code owner approval"** on `main` branch (external, post-push)
4. **Verify MR template UI** — open a new MR in GitLab and confirm template appears (post-push)
5. **File hardening ticket** for `_instructor_mode` UnboundLocalError if not already filed

---

## Test Invocation

```bash
PYTHONPATH="C:/Users/prora/AppData/Roaming/Python/Python313/site-packages" python -m pytest tests/ -v --timeout=30
```

System: Python 3.13.2 (`C:\Python313\python.exe`), pytest 9.0.2 in user site-packages.

---

# Sprint Status - README Investigation and Maintenance Closure

> Generated: 2026-06-18
> Plan section: `plans/from_chat/20260420_000000_score_improvement.md` -> `Sprint Update - 2026-06-18: README Investigation and Maintenance Closure`

## Task Status

| Task | File(s) | Status | Notes |
|------|---------|--------|-------|
| README-INV-20260618 | `README.md`, `plans/from_chat/20260420_000000_score_improvement.md`, `reports/STATUS.md` | COMPLETE | README investigated and updated from repo evidence; plan/status amended in place |

## Verification Performed

| Check | Status |
|-------|--------|
| `.venv` CLI `--help` smoke check | PASS |
| `.venv` `list-families` smoke check | PASS with documented OneDrive/Chroma caveats |
| Ops/pattern helper `--help` checks | PASS |
| `pytest tests/test_doc_validators.py tests/test_evidence_validators.py -v --timeout=120` | PASS (`22 passed`) |
| `scripts/validation/check_doc_links.py README.md` | PASS |
| `scripts/validation/check_evidence_circularity.py` | PASS |
| README mojibake check (`rg "â|�" README.md`) | PASS |

## Remaining Follow-Ups

- Normalize Markdown write default documentation versus `config/global.json`.
- Standardize gist token environment variables across examples and configs.
- Repair stale internals in ops helper scripts before presenting them as primary copy/paste workflows.
- Update README eval-claim parsing for the rewritten family baseline table.
- Add a lightweight live-smoke profile for external dependencies.

## Closure

CLOSED after the README update, verification, plan/status update, and Git commit are complete.
