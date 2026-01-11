# Sonnet: Repo Hardening + Multi-Family Scale-out + Gist Publishing

**Mission:** Make example-reviewer production-grade, implement multi-family scaling (30+ families), and add optional GitHub gist publishing for changed snippets.

**Engineer:** Claude Sonnet 4.5 (Acting as Repo Hardener + Scale-out Implementer)
**Started:** 2026-01-11
**Branch:** feature/hardening-multifamily-gistpublish

---

## Phase 0: Baseline Capture

### Repository State

**Branch Information:**
```
Current branch: feature/hardening-multifamily-gistpublish
Parent branch: main
Base commit: c1537c4b024a0ec693d151b17304807189b6602b
```

**Recent Commits (main):**
```
c1537c4 feat: complete GitHub Gist hardening (HARD-003, HARD-004, HARD-005)
91d6dc1 docs: add HARD-002 complete evidence with 5.0/5 score
c475b88 test: complete HARD-002 integration test suite
e385ef6 test: add comprehensive gist parsing regression tests
3841547 fix: add support for mixed-format gist shortcodes
```

**Git Status:**
- Clean working directory
- No uncommitted changes
- Untracked file: nul (artifact from Windows commands - will ignore)

### Directory Structure

**Source Files (src/):**
- cli.py - Command-line interface
- database.py - SQLite database layer
- discovery_service.py - Page discovery
- gist_service.py - GitHub Gist integration
- patching_service.py - Code patching
- workspace_manager.py - .NET workspace management
- validation_orchestrator.py - Validation orchestration
- snippet_locator.py - Snippet location tracking
- pattern_registry.py - Pattern-based fixes
- ollama_integration.py - LLM integration
- telemetry.py - Telemetry and logging
- example_fixer.py - Legacy fixer
- page_scanner.py - Legacy scanner
- placeholder_patcher.py - Placeholder patching
- review_orchestrator.py - Legacy orchestrator
- review_inmemory_blog.py - Legacy specific fix

**Test Files (tests/):**
- conftest.py - Pytest configuration with --integration flag support
- test_gist_*.py - Gist-related tests (service, parsing, patching, cache, database, integration)
- test_cli_paths.py - CLI path tests
- test_cache_validation.py - Cache validation tests
- benchmark_gist_performance.py - Performance benchmarks
- fixtures/gist_fixtures.py - Test fixtures

**Configuration Files:**
- config/families/test.json - Old format (flat structure, Newtonsoft.Json)
- config/families/smoke.json - New format (canonical structure, Newtonsoft.Json, nuget_config, code_defaults)

**Documentation (docs/):**
- api-reference.md - API documentation
- architecture.md - System architecture
- configuration.md - Configuration guide
- development-guide.md - Development workflow
- operations.md - Operations guide
- patching-strategies.md - Patching strategies
- performance.md - Performance considerations
- security.md - Security best practices
- testing-guide.md - Testing guide
- troubleshooting.md - Troubleshooting guide

**Specifications (specs/):**
- api-reference.md - API specs
- architecture.md - Architecture specs
- configuration.md - Configuration specs
- database-schema.md - Database schema specs
- patching-strategies.md - Patching strategy specs

### Bootstrap Files Assessment

#### ✅ schema.sql
- **Location:** Repository root
- **Status:** EXISTS
- **CLI Reference:** src/cli.py line 43 uses `self.script_dir / "schema.sql"` ✓
- **Content:** Complete SQLite schema with:
  - Core tables: pages, snippets, snippet_versions
  - Execution tracking: runs, run_events
  - Validation tracking: snippet_issues, fixes_applied, build_attempts
  - Gist support: gists, gist_files
  - Views: v_active_snippets, v_run_statistics, v_pages_needing_attention, v_snippet_validation_summary
  - Triggers: Auto-update timestamps and counters
  - Schema version tracking

#### ✅ requirements.txt
- **Location:** Repository root
- **Status:** EXISTS
- **Content:** Comprehensive dependencies:
  ```
  sqlalchemy>=2.0.0
  requests>=2.31.0
  markdown-it-py>=3.0.0
  python-frontmatter>=1.0.0
  regex>=2023.10.0
  python-json-logger>=2.0.0
  jinja2>=3.1.0
  pytest>=7.4.0
  pytest-asyncio>=0.21.0
  ```
- **Assessment:** Good coverage, but missing explicit version pin for stability
- **Note:** pytest not currently installed in environment

#### ⚠️ .gitignore
- **Location:** Repository root
- **Status:** EXISTS but needs refinement
- **Current Issues:**
  1. Ignores entire `reports/` directory - but we're creating engineering log there
  2. Ignores entire `cache/` directory - correct for runtime
  3. Ignores entire `data/` directory - correct for runtime
  4. Has `/Python313Libsite-packages` - should be ignored (vendor directory)
  5. Missing `.pytest_cache/` (currently tracked)
- **Action Required:** Adjust .gitignore to allow engineering logs in reports/ while blocking other artifacts

### CLI Analysis

**Commands Available:**
- `init-db` - Initialize database (uses schema.sql correctly) ✓
- `discover --family <family> [--max-pages <n>]` - Discover snippets
- `validate --family <family> [--max-snippets <n>] [--no-ollama]` - Validate snippets
- `db-status [--family <family>]` - Database status
- `check-ollama` - Check Ollama availability
- `patch --family <family> [--dry-run]` - Patch verified snippets

**Issues Identified:**
1. ❌ **PHASE 3 Issue:** `patch` command does NOT expose `--gist-mode` parameter
   - CLI line 362: `def patch(self, family: str, dry_run: bool = False)`
   - PatchingService is called without gist_mode argument (line 384)
   - Default gist mode not specified

2. ⚠️ **Cache Location Inconsistency:**
   - CLI line 70: Uses `self.script_dir / "data" / "gist_cache"` for gist cache
   - Should use `cache/gists/` for consistency with architecture

### Family Config Schema Analysis

**Two formats exist:**

**Old Format (test.json):**
```json
{
  "name": "test",
  "package_id": "Newtonsoft.Json",
  "version": "latest_stable",
  "target_framework": "net6.0",
  "skip_patterns": [],
  "ollama_enabled": false
}
```

**Canonical Format (smoke.json):**
```json
{
  "family": "smoke",
  "display_name": "Smoke Test Family",
  "content_pattern": "**/smoke/**/*.md",
  "nuget_config": {
    "primary_package": {
      "name": "Newtonsoft.Json",
      "version_strategy": "latest_stable"
    },
    "target_frameworks": ["net8.0"],
    "version_strategy": "latest_stable"
  },
  "code_defaults": {
    "default_usings": ["Newtonsoft.Json"]
  },
  "patterns": [],
  "non_existent_apis": []
}
```

**Schema Differences:**
- test.json uses flat `package_id`, smoke.json uses nested `nuget_config.primary_package.name`
- test.json uses single `target_framework`, smoke.json uses array `target_frameworks`
- smoke.json has `code_defaults.default_usings` for Program.cs generation
- smoke.json has `content_pattern` for discovery
- smoke.json has `display_name` for UX
- test.json uses `name`, smoke.json uses `family`

**Action Required:** Implement backward-compatible config normalization

### Test Collection Issue

**Status:** Cannot verify yet (pytest not installed)
**Suspected Issue:** test_gist_integration.py line 26 imports from fixtures.gist_fixtures at module level
**Test Infrastructure:**
- conftest.py has proper --integration flag support ✓
- conftest.py implements pytest_collection_modifyitems to skip integration tests by default ✓
- Integration tests marked with @pytest.mark.integration ✓

**Action Required:** Install requirements and verify pytest collection works

---

## Phase 1: Bootstrap Hygiene

### Status: PENDING

### Planned Actions:

1. **Refine .gitignore**
   - Keep reports/ tracked for engineering logs
   - Add reports/SONNET_hardening_and_scaleout.md to exceptions
   - Add .pytest_cache/ to ignore list
   - Keep data/, cache/, workspaces/ ignored

2. **Verify schema.sql integration**
   - Confirm init-db command works
   - Verify schema creates all required tables

3. **Install and verify requirements**
   - Run: pip install -r requirements.txt
   - Verify pytest collection works

---

## Next Steps

1. Complete Phase 1: Bootstrap hygiene
2. Install requirements and fix any test collection issues (Phase 2)
3. Align CLI with gist-mode and cache path (Phase 3)
4. Implement multi-family scaling (Phase 4)
5. Add gist publishing capability (Phase 5)
6. Final gating and merge (Phase 6)

---

**Log Format:** This is an append-only log. New entries will be added below as work progresses.
