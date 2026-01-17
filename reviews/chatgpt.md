I reviewed all 5 healing plans you attached. Overall they’re well-structured (gap→taskcards, scoped paths, acceptance checks, hard rules), but a few of them need **alignment with the current repo layout/implementation** to avoid “fixing the wrong thing” or duplicating what already exists.

## Cross-cutting suggestions (apply to all plans)

1. **Update file paths + entrypoints to match the current repo**

* Multiple plans refer to `src/cli.py`, `src/telemetry.py`, `src/patching_service.py`, etc. but this repo is organized around `src/cli/main.py`, `src/services/*`, `src/core/*`, and the pipeline orchestrator already contains commit logic in Phase F. This mismatch is also explicitly called out in your infrastructure hardening plan. 

2. **Avoid duplication: re-scope taskcards around what already exists**

* Example: auto-commit is *not* “completely missing” in this repo: Phase F already stages + commits touched files when `global_config.git.enabled` and not `dry_run`. So the healing work should focus on *config toggles, commit message templating, safety/rollback, and telemetry association*, rather than building a second commit system in another service. 

3. **Add a “Repo Reality Check” step at the top of each plan**

* 10–15 minutes of `grep`/`ripgrep` validation (does the target class/method exist? which module owns it now?) prevents wasted cycles—especially because several plans cite methods/classes that don’t exist in sources but appear in `__pycache__` remnants (your infra plan already flags this). 

---

## Plan-by-plan verification + concrete improvements

### 1) Infrastructure Hardening

This plan is the most “foundational” and should likely be done first because it corrects the contract and eliminates repo confusion. 

**Suggestions**

* **IH-02 (CLI entry point mismatch):** instead of introducing `setup.py` immediately, a minimal/low-risk fix is:

  * add a top-level `cli/` package with `__main__.py` that calls `src.cli.main:main()`, so `python -m cli ...` becomes true without packaging work. (Your plan already hints at `cli/__main__.py` as a deliverable.) 
* **IH-03 (docs alignment):** add an explicit acceptance check: “Every referenced module path exists in `src/`” (e.g., a grep list of module names + a `python -c "import ..."` smoke test). You already include this idea; make it a hard gate. 
* **IH-04 (repo hygiene):** good call to remove `__pycache__` + add `.gitignore`, but add one more guard:

  * “Before deleting any ‘empty’ package, confirm it’s not imported anywhere” (grep imports). This prevents breaking latent imports even if they’re not executed in your typical run. 

**Priority note:** I agree with your order: IH-02 → IH-03 → IH-04. 

---

### 2) Auto-Commit of Touched Files

The plan is solid, but it currently assumes a patching service + CLI file names that don’t match the repo, and it also assumes git commit is missing. 

**Key reality check:** Phase F in `src/pipeline/orchestrator.py` already stages + commits touched files when git is enabled. So AC-01 should be refactored into: “Make existing commit behavior configurable and safe” rather than “implement commit from scratch.” 

**Suggestions**

* **Unify config hierarchy**: you already have `FamilyConfig.auto_commit` and `commit_message_template` in config, plus `global_config.git.enabled`. Make the precedence explicit in the plan:

  * CLI flag (if you add one) > family `auto_commit` > global `git.enabled` (or vice versa), but document it and test it. 
* **Commit message templating**: your repo already supports a global template; the plan should prefer using `family_config.commit_message_template` when present, else fall back to global. 
* **Telemetry association**: don’t build a new telemetry client just for commit association—your telemetry layer already has an associate-commit concept; ensure Phase F calls it *only after* a successful commit and captures the commit hash. (Your plan’s AC-03 dependency notes are good.) 
* **Rollback**: AC-04 is valuable, but consider making it “backup branch optional” and “rollback command explicit.” Your plan already calls out risk and makes it medium priority, which is right. 

---

### 3) Configurable Code Discovery

This is a strong plan and matches the current reality: discovery has hardcoded `FENCE_PATTERN`, gist patterns, and `VALIDATABLE_LANGUAGES`. 

**Suggestions**

* **Use Pydantic models, not dataclasses**: your config system is Pydantic-based (`BaseModel`), so define `DiscoveryPatternsConfig`, `FilterConfig`, etc. as Pydantic models for consistent validation + JSON schema. 
* **Regex safety**: add a guardrail for catastrophic regex (especially with `DOTALL` + greedy `.*?`):

  * acceptance check: “on a large markdown file, discovery completes under X seconds” (even a soft target helps).
* **Language normalization**: expand normalization to handle fences like `c# or `csharp with punctuation—your plan’s alias handling is good; just ensure the extraction captures non-`\w` cases (today `(\w*)` won’t capture `c#`). 
* **Filtering telemetry**: great idea; make the metrics explicit (e.g., `filtered_min_lines`, `filtered_exclude_regex`, `filtered_comments_only`) so you can tune configs without guessing. 

---

### 4) Intent Drift Prevention

This is strategically important and the plan is coherent: it identifies the drift sources and proposes “two-code review”, drift gating, anchored prompts, and vector DB hygiene. 

**Suggestions**

* **ID-04 first is correct**: Two-code review is low-risk and immediately increases correctness by giving Phase E the context it lacked. 
* **Drift metric implementation detail**: don’t instantiate a new `SentenceTransformer()` inside drift scoring each time (costly). Instead:

  * reuse the existing embedding model instance from the vector DB service when available, or compute drift using cheap metrics by default and only use embeddings when enabled. (Your plan already includes multi-metric options; make this the default behavior.) 
* **Be explicit about “what is drifted relative to what”**:

  * For acceptance gates, I recommend drift computed against **original_code** (teaching intent), not just “previous attempt”, otherwise the system may converge to something compilable but far from the doc’s intent.
* **Vector DB contamination**: the selective storage/cleanup tasks are excellent—just add one more acceptance check: “search results never return examples above drift threshold when exclude_high_drift=true.” 

---

### 5) Telemetry Fixes

This plan is directionally good (tests, HTTP robustness, richer metrics), but it appears written for a different telemetry implementation (a `TelemetryClient` in `src/telemetry.py` + NDJSON dual-write). In this repo, telemetry is split between `src/services/telemetry_service.py` (HTTP + DB) and `src/core/telemetry.py` (phase timing + export). 

**Suggestions**

* **Re-scope TM-01**: instead of `record_timing()` on a TelemetryClient, add timing aggregation where timing actually happens:

  * either extend `track_phase_timing()` / exported telemetry artifacts, or add timing fields to the run record via `TelemetryService.update_run()`.
* **TM-02 is partially redundant**: TelemetryConfig already has `http_api_enabled`, `http_api_url`, timeouts, retries. The plan should focus on “verify API schema compliance + idempotency + failure modes” and add tests around the existing service instead of adding a parallel env-var system. 
* **Most valuable immediate fix**: TM-03 “add tests” should be your near-term goal—tests for:

  * start_run posts (or skips) correctly,
  * update_run patches correctly,
  * failures degrade gracefully (don’t crash pipeline),
  * commit association is persisted + posted when enabled. 

---

## Suggested overall execution order (lowest risk → highest leverage)

1. **Infrastructure hardening (IH-02 → IH-03)** to align contracts and stop path drift. 
2. **Configurable discovery (CD-01 → CD-02)** to improve Phase A quality + reuse. 
3. **Intent drift quick win (ID-04)** to prevent “verified but misleading” docs. 
4. **Telemetry tests + schema validation (TM-03 + light TM-02 adjustments)** to make runs trustable. 
5. **Auto-commit alignment**: refactor AC plan to “enhance Phase F commit” (config precedence + template + rollback). 

If you want, I can rewrite each healing plan’s **Allowed paths / Acceptance checks** to match the current repo structure (so the taskcards are immediately executable without guesswork).
