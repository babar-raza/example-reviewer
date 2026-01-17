# Auto-Commit of Touched Files Healing Plan

## Context

⚠️ **CRITICAL CORRECTION**: This plan was originally written assuming git integration was "completely missing", but **Phase F in `src/pipeline/orchestrator.py` already implements git commit functionality** (lines 1211-1349).

**Current Reality**:
- Phase F stages and commits touched files when `global_config.git.enabled = true` and not `dry_run`
- Commit message templating already exists via `global_config.git.commit_message_template`
- Git root finding, file staging (`git add`), and commit creation are fully implemented
- Commit hash is captured but not yet associated with telemetry runs
- Co-author tag is hardcoded in Phase F (lines 1309+)

**Actual Gaps** (refined from original assumptions):
1. **Config hierarchy unclear**: No explicit precedence between CLI flag, family config, and global config
2. **Family-level templating missing**: Cannot override commit message per family
3. **Telemetry association incomplete**: Commit hash not sent to telemetry API after successful commit
4. **Rollback mechanism missing**: No safety net for undoing automated commits
5. **Testing incomplete**: Phase F commit behavior lacks comprehensive tests

**Telemetry Integration:** Git commits should be associated with telemetry runs via TelemetryService `POST /api/v1/runs/{event_id}/associate-commit`.

**Reference:** See [src/pipeline/orchestrator.py:1211-1349](../src/pipeline/orchestrator.py) for existing Phase F implementation

## Repo Reality Check

**Purpose**: Verify assumptions about git integration before making changes.

### Validation Commands

```bash
# 1. Verify Phase F git commit implementation exists
grep -n "def _run_finalization_phase" src/pipeline/orchestrator.py
grep -n "git.enabled" src/pipeline/orchestrator.py
grep -A 80 "# Attempt git commit" src/pipeline/orchestrator.py | head -100

# 2. Check if patching_service.py exists (plan assumes it does)
[ -f src/patching_service.py ] && echo "EXISTS" || echo "MISSING: src/patching_service.py"
[ -f src/services/patching_service.py ] && echo "EXISTS" || echo "MISSING: src/services/patching_service.py"

# 3. Verify CLI entry point
[ -f src/cli.py ] && echo "EXISTS" || echo "MISSING: src/cli.py"
[ -f src/cli/main.py ] && echo "EXISTS: src/cli/main.py" || echo "MISSING"

# 4. Check git config in global.json
grep -A 10 '"git"' config/global.json

# 5. Verify telemetry service exists
[ -f src/services/telemetry_service.py ] && echo "EXISTS: TelemetryService" || echo "MISSING"

# 6. Check commit message template
grep "commit_message_template" config/global.json
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| Git integration missing | ❌ **INCORRECT** | Phase F lines 1241-1349 implement full git commit |
| No git staging | ❌ **INCORRECT** | Phase F lines 1283-1297 stage files with `git add` |
| `src/patching_service.py` exists | ❌ **INCORRECT** | No patching service - Phase F handles file updates |
| `src/cli.py` exists | ❌ **INCORRECT** | Actual is `src/cli/main.py` |
| No commit message template | ❌ **INCORRECT** | `global_config.git.commit_message_template` exists at config line 25 |
| No telemetry association | ✅ **PARTIALLY CORRECT** | Commit hash captured but not sent to telemetry API |
| No rollback mechanism | ✅ **CORRECT** | No safety net for automated commits |
| No family-level config | ✅ **CORRECT** | No `family_config.commit_message_template` override |

### Go/No-Go Decision

⚠️ **RESCOPE REQUIRED** - Original plan assumes non-existent files and duplicate functionality.

**Revised Scope**:
- **AC-01**: ~~Implement git commit from scratch~~ → **Add CLI flag for commit control & comprehensive tests for Phase F**
- **AC-02**: ~~Add git config~~ → **Enhance existing config with family-level overrides & precedence rules**
- **AC-03**: ~~Implement commit messages~~ → **Add telemetry association to Phase F existing commits**
- **AC-04**: **Keep rollback mechanism** (valid new feature)

**Estimated Reality Check Time**: 15 minutes

---

## Gap → Taskcard Mapping (REVISED)

| Gap/Blocker ID | Description | Taskcard ID(s) | Status |
|----------------|-------------|----------------|--------|
| AC-GAP-01 | ~~No git commit automation~~ | ~~AC-01~~ | ✅ **EXISTS** - Phase F implements this |
| AC-GAP-02 | ~~No git staging automation~~ | ~~AC-01~~ | ✅ **EXISTS** - Phase F implements this |
| AC-GAP-03 | Config hierarchy unclear (CLI > family > global) | AC-02 | ⚠️ Needs clarification & testing |
| AC-GAP-04 | No family-level commit message template override | AC-02 | ⚠️ Needs addition |
| AC-GAP-05 | No rollback mechanism - manual git reset required | AC-04 | ⚠️ Needs implementation |
| AC-GAP-06 | Commit hash not sent to telemetry API | AC-03 | ⚠️ Needs telemetry call in Phase F |
| AC-GAP-07 | Phase F commit logic lacks tests | AC-01 | ⚠️ Needs comprehensive tests |

---

## Taskcard AC-01: ~~Implement Auto-Commit Core~~ → Add Tests & CLI Flags for Phase F

⚠️ **RESCOPED** - This taskcard originally assumed git commit was missing. **Phase F already implements git commit** (orchestrator.py:1211-1349).

**New Focus**: Add CLI flags to control Phase F git behavior and comprehensive tests for existing functionality.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes AC-GAP-07 (Phase F lacks tests), partial AC-GAP-03 (CLI flag control)

**Role:** Senior engineer delivering comprehensive tests and CLI control for existing Phase F git functionality.

---

### ⚠️ CRITICAL: Use Existing Phase F Implementation

**DO NOT** implement git commit from scratch in a hypothetical `PatchingService`. **Instead**:
1. Phase F already stages files (lines 1283-1297)
2. Phase F already commits (lines 1299-1330)
3. Phase F already captures commit hash (line 1334)
4. Work is to **enhance** Phase F, not rebuild it

---

### Scope

**Fix:**
- Add `auto_commit: bool` parameter to `PatchingService.patch_verified_snippets()` method
- Implement git staging (`git add`) for all files in `results['modified_files']` set
- Implement git commit with generated message after successful patching
- Add subprocess calls to git commands with proper error handling
- Ensure auto-commit only happens when patching succeeds (no errors)
- Support dry-run mode (no git commit when `--dry-run` flag set)
- Return commit SHA from git commit operation for telemetry integration

**Allowed paths:**
- `src/patching_service.py` - add auto-commit logic
- `src/cli.py` - add `--auto-commit` flag
- `test_patching_auto_commit.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python src/cli.py patch --family zip --auto-commit`
- Verify git commit created with modified files staged
- Run `git log -1` to see commit message (should reference family and patch count)
- Run `git log -1 --format=%H` to verify commit SHA captured
- Run `python src/cli.py patch --family zip --auto-commit --dry-run`
- Verify no git commit created in dry-run mode
- Run `git diff` after auto-commit to verify no uncommitted changes remain

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest test_patching_auto_commit.py -v` passes
- Test happy path: auto-commit creates git commit with modified files
- Test commit SHA returned from git commit operation
- Test dry-run: no git commit created when --dry-run flag set
- Test failure path: git commit skipped when patching has errors
- Test edge case: no modified files → no git commit
- Test edge case: git not available → graceful error message

**Config respected end-to-end:**
- Auto-commit only when `--auto-commit` flag present (opt-in behavior)
- Dry-run mode disables auto-commit
- Existing workflows without `--auto-commit` flag unchanged

**No mock data in production paths:**
- Real git commands executed in production
- Mock git subprocess calls in tests

### Deliverables

1. **New test file `tests/test_phase_f_git_integration.py`:**
   - Comprehensive tests for existing Phase F git functionality
   - Test class `TestPhaseFGitCommit`:
     - `test_phase_f_creates_commit_when_git_enabled`
     - `test_phase_f_skips_commit_when_git_disabled`
     - `test_phase_f_returns_commit_sha`
     - `test_phase_f_stages_all_touched_files`
     - `test_phase_f_uses_commit_message_template`
     - `test_dry_run_disables_commit`
     - `test_commit_skipped_when_no_files_touched`
     - `test_git_not_available_graceful_error`
   - Use temporary git repository for tests (initialize with `git init`)
   - Mock subprocess calls or use real git in temp directory
   - Verify git log shows commit after Phase F
   - Verify commit SHA is valid 40-character hex string
   - Verify commit message matches template

2. **Updated `src/cli/main.py` - add CLI flags for Phase F git control:**
   - Add flags to `run` command:
     ```python
     parser_run.add_argument('--enable-git-commit', action='store_true',
                             dest='enable_git_commit',
                             help='Force enable git commit in Phase F (overrides config)')
     parser_run.add_argument('--disable-git-commit', action='store_false',
                             dest='enable_git_commit',
                             help='Force disable git commit in Phase F (overrides config)')
     parser_run.set_default(enable_git_commit=None)  # None = use config
     ```
   - Pass flag to orchestrator's `run_family()` method
   - Log commit SHA if Phase F creates commit:
     ```python
     stats = orchestrator.run_family(...)
     if 'commit_sha' in stats:
         logger.info(f"Phase F created commit: {stats['commit_sha']}")
     ```

3. **Updated `src/pipeline/orchestrator.py` - expose CLI control:**
   - Accept `enable_git_commit: Optional[bool] = None` parameter in `run_family()`
   - Pass parameter to `_run_finalization_phase()`
   - Phase F already has git implementation - just needs parameter plumbing

4. **Integration test script `tests/integration/test_phase_f_cli_flags.sh`:**
   - Test `--enable-git-commit` flag forces commit
   - Test `--disable-git-commit` flag prevents commit
   - Test flags override config settings
   - Verify commit SHA captured and logged

5. **Forward-compatible migration:**
   - Existing CLI calls without flags behave exactly as before
   - Phase F existing git behavior unchanged
   - CLI flags provide explicit control when needed

### Hard Rules

- ✅ Keep public signatures: Add optional parameter with default (backward compatible)
- ✅ No network in offline tests: Git operations are local filesystem only
- ✅ Keep entrypoints in parity: CLI-only feature (no API/UI yet)
- ✅ Mock vs Live mode: Tests use temp git repos or mock subprocess; production uses real git
- ✅ Deterministic runs: Tests create predictable commits in temp repos
- ✅ No new deps: Use built-in `subprocess` module
- ✅ Keep code/docs/tests in sync: Update docstrings for new parameters

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Git commits created correctly; all modified files staged; commit messages valid; commit SHA captured |
| **Completeness** | Works with --auto-commit flag; respects dry-run; handles errors gracefully; returns commit SHA |
| **Robustness** | Git not available → clear error; commit fails → logged warning; doesn't crash pipeline |
| **Testability** | Tests verify commits created; tests verify commit SHA; tests verify dry-run behavior; tests cover edge cases |
| **Documentation** | Docstrings explain auto-commit behavior; CLI help text clear |
| **Integration** | Works seamlessly with existing patching; backward compatible; opt-in behavior; prepares for telemetry integration |

### Now (Runbook)

```bash
# 1. Verify Phase F git implementation exists
grep -A 100 "def _run_finalization_phase" src/pipeline/orchestrator.py | grep -A 50 "Attempt git commit"
# Result: Lines 1251-1334 show full git implementation

# 2. Create comprehensive test file for Phase F git functionality
cat > tests/test_phase_f_git_integration.py << 'EOF'
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.pipeline.orchestrator import Orchestrator
from src.core.database import Database
from src.core.config import load_config

@pytest.fixture
def temp_git_repo():
    """Create temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(['git', 'init'], cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True)
        yield repo_path

class TestPhaseFGitCommit:
    def test_phase_f_creates_commit_when_git_enabled(self, temp_git_repo):
        # Test Phase F creates commit when global_config.git.enabled = true
        pass

    def test_phase_f_returns_commit_sha(self, temp_git_repo):
        # Test Phase F returns commit SHA in stats dict
        pass

    # More tests...
EOF

# 3. Implement all test cases
# Test: Phase F creates commit, skips when disabled, dry-run behavior, etc.

# 4. Run tests
pytest tests/test_phase_f_git_integration.py -v

# 5. Add CLI flags to src/cli/main.py
# Read existing run command
grep -A 30 "parser_run = subparsers.add_parser('run'" src/cli/main.py

# Add --enable-git-commit and --disable-git-commit flags
# Update orchestrator.run_family() call to pass enable_git_commit parameter

# 6. Update orchestrator to accept CLI override
# Add enable_git_commit parameter to run_family() and _run_finalization_phase()

# 7. Integration test with real CLI
# With git enabled in config
python -m src.cli.main run --family zip --max-examples 1

# Verify commit created
git log -1

# With git disabled via CLI flag
python -m src.cli.main run --family zip --max-examples 1 --disable-git-commit

# Verify no commit created
git log -1  # Should show previous commit, not new one

# With git enabled via CLI flag (overriding config)
python -m src.cli.main run --family zip --max-examples 1 --enable-git-commit

# Verify commit created even if config says disabled
git log -1
```

---

## Taskcard AC-02: ~~Add Auto-Commit Configuration~~ → Enhance Phase F Config Hierarchy

⚠️ **RESCOPED** - Global git config already exists (config/global.json lines 23-28). This taskcard now focuses on adding **family-level overrides** and **CLI flags** for Phase F.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes AC-GAP-03 (Config hierarchy unclear), AC-GAP-04 (No family-level commit message template override)

**Role:** Senior engineer enhancing Phase F configuration with family-level overrides and CLI control.

---

### ⚠️ CRITICAL: Enhance Existing Phase F Config, Don't Duplicate

**Phase F already has**:
- `global_config.git.enabled` (line 1241 in orchestrator.py)
- `global_config.git.commit_message_template` (line 1306 in orchestrator.py)
- Git staging and commit implementation (lines 1283-1330)

**Work is to ADD**:
1. Family-level overrides in `config/families/*.json`
2. CLI flags `--enable-git-commit` / `--disable-git-commit` in `src/cli/main.py`
3. Config hierarchy: CLI flag > family config > global config

---

### Scope

**Fix:**
- Add `git.enabled` and `git.commit_message_template` to family configuration schema (`config/families/*.json`)
- Enhance Phase F to check family config before global config
- Add CLI flags `--enable-git-commit` and `--disable-git-commit` to `src/cli/main.py`
- Document config precedence: CLI flag > family config > global config > default (False)
- Add tests for config hierarchy resolution

**Allowed paths:**
- `src/pipeline/orchestrator.py` - enhance Phase F config resolution
- `src/cli/main.py` - add CLI flags for git commit control
- `config/families/zip.json` - example family-level git configuration
- `tests/test_auto_commit_config.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add `"git": {"enabled": true}` to `config/families/zip.json`
- Run `python -m src.cli.main run --family zip` (without CLI flag)
- Verify git commit created by Phase F (family config enables it)
- Run `python -m src.cli.main run --family zip --disable-git-commit`
- Verify no git commit created (CLI flag overrides family config)
- Set `"git": {"enabled": false}` in global config, `"git": {"enabled": true}` in zip family config
- Run `python -m src.cli.main run --family zip` - verify commit created (family overrides global)

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_auto_commit_config.py -v` passes
- Test family config enables git commit in Phase F
- Test CLI flag overrides family config
- Test global config used as fallback
- Test hierarchy: CLI flag > family config > global config > default

**Config respected end-to-end:**
- All three configuration levels work correctly (CLI > family > global)
- CLI flag has highest precedence
- Default remains False (opt-in, not opt-out)

**No mock data in production paths:**
- Real config files used in production
- Mock config files in tests

### Deliverables

1. **Updated `src/pipeline/orchestrator.py` - enhance Phase F config resolution:**
   - Modify `_run_finalization_phase()` to check config hierarchy:
     ```python
     def _run_finalization_phase(
         self,
         family: str,
         run_id: str,
         dry_run: bool,
         enable_git_commit: Optional[bool] = None,  # NEW: CLI override
     ) -> Dict[str, Any]:
         # Determine git.enabled from hierarchy
         if enable_git_commit is not None:
             git_enabled = enable_git_commit  # CLI flag wins
         elif family in self.family_configs and 'git' in self.family_configs[family]:
             git_enabled = self.family_configs[family]['git'].get('enabled', self.global_config.git.enabled)
         else:
             git_enabled = self.global_config.git.enabled  # Global fallback

         if dry_run or not git_enabled:
             return stats

         # ... rest of Phase F git commit logic ...
     ```
   - Add family-level commit message template resolution:
     ```python
     # Get commit message template (family overrides global)
     if family in self.family_configs and 'git' in self.family_configs[family]:
         commit_template = self.family_configs[family]['git'].get(
             'commit_message_template',
             self.global_config.git.commit_message_template
         )
     else:
         commit_template = self.global_config.git.commit_message_template
     ```

2. **Updated `src/cli/main.py` - add CLI flags:**
   - Add git commit control flags to `run` command:
     ```python
     parser_run.add_argument('--enable-git-commit', action='store_true', dest='enable_git_commit',
                             help='Enable git commit in Phase F (overrides config)')
     parser_run.add_argument('--disable-git-commit', action='store_false', dest='enable_git_commit',
                             help='Disable git commit in Phase F (overrides config)')
     parser_run.set_default(enable_git_commit=None)  # None means use config
     ```
   - Pass CLI flag to orchestrator:
     ```python
     orchestrator.run_family(
         family=args.family,
         dry_run=args.dry_run,
         enable_git_commit=args.enable_git_commit,  # NEW: Pass CLI override
         ...
     )
     ```

3. **Updated `config/families/zip.json` - add family-level git config:**
   - Add optional git configuration:
     ```json
     {
       "family": "zip",
       "git": {
         "enabled": true,
         "commit_message_template": "fix(zip): apply {patch_count} patches\n\n{details}"
       },
       ...
     }
     ```
   - Document: `// git: Family-level git configuration (overrides global config)`

4. **New test file `tests/test_auto_commit_config.py`:**
   - `test_family_config_overrides_global`
   - `test_cli_flag_overrides_family_config`
   - `test_global_config_used_as_fallback`
   - `test_config_hierarchy_correct`
   - `test_family_commit_message_template`
   - `test_default_is_false_opt_in`

5. **Forward-compatible migration:**
   - Existing family configs without `git` field use global config (backward compatible)
   - Existing CLI calls without flags work unchanged
   - Phase F existing behavior preserved when configs not present

### Hard Rules

- ✅ Keep public signatures: CLI argument parsing extended (backward compatible)
- ✅ Keep entrypoints in parity: CLI-only feature
- ✅ Deterministic runs: Config hierarchy deterministic and documented
- ✅ No new deps: Use existing `os`, `json` libraries
- ✅ Keep code/docs/tests in sync: Document config hierarchy in docstrings

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Config hierarchy works correctly; CLI flag always wins; env var fallback works |
| **Completeness** | All three config levels supported; --no-auto-commit flag works; defaults sensible |
| **Robustness** | Invalid config values handled gracefully; missing config keys don't crash |
| **Testability** | Tests verify hierarchy; tests verify each config level independently |
| **Documentation** | Config hierarchy documented; .env.example clear; family config commented |
| **Integration** | Works seamlessly with AC-01 core functionality; backward compatible |

### Now (Runbook)

```bash
# 1. Read existing CLI patch command argument parsing
grep -A 30 "def patch" src/cli.py

# 2. Update CLI argument parsing
# Change --auto-commit to support None default:
#   parser.add_argument('--auto-commit', action='store_true', default=None, dest='auto_commit')
#   parser.add_argument('--no-auto-commit', action='store_false', dest='auto_commit')

# 3. Implement config hierarchy logic
# Add after family config loaded:
#   auto_commit_config = family_config.get('auto_commit', None)
#   auto_commit_env = os.getenv('AUTO_COMMIT_ENABLED', 'false').lower() == 'true'
#
#   if args.auto_commit is not None:
#       auto_commit = args.auto_commit
#   elif auto_commit_config is not None:
#       auto_commit = auto_commit_config
#   else:
#       auto_commit = auto_commit_env

# 4. Update family config example
# Add to config/families/zip.json:
#   "auto_commit": false

# 5. Update .env.example
echo "AUTO_COMMIT_ENABLED=false" >> .env.example

# 6. Create test file
# Tests for config hierarchy...

# 7. Run tests
pytest test_auto_commit_config.py -v

# 8-10. Integration tests (family config, CLI override, env var)
```

---

## Taskcard AC-03: ~~Implement Commit Message Generation~~ → Add Telemetry Association to Phase F

⚠️ **RESCOPED** - Phase F already generates commit messages (line 1306 in orchestrator.py). **TelemetryService.associate_commit()** already exists (line 222 in telemetry_service.py). This taskcard now focuses on **calling** the existing telemetry method from Phase F.

**Status:** Not Started (Rescoped)

**Gap Linkage:** Fixes AC-GAP-06 (Commit hash not sent to telemetry API)

**Role:** Senior engineer integrating Phase F git commits with existing TelemetryService for traceability.

---

### ⚠️ CRITICAL: Use Existing TelemetryService, Don't Create New Implementation

**Phase F already has**:
- Commit message generation with template (line 1306 in orchestrator.py)
- Commit hash capture (line 1334: `commit_hash = commit_result.stdout.strip()`)
- Co-author tag injection (lines 1309-1311)

**TelemetryService already has**:
- `associate_commit(event_id, commit_hash, ...)` method (line 222 in services/telemetry_service.py)
- HTTP API integration with POST /api/v1/runs/{event_id}/associate-commit

**Work is to ADD**:
1. Call `TelemetryService.associate_commit()` from Phase F after successful commit
2. Pass commit metadata (hash, source=llm, author, timestamp) to existing method
3. Add tests verifying telemetry association happens

---

### Scope

**Fix:**
- Call `TelemetryService.associate_commit()` from Phase F after git commit succeeds
- Extract commit metadata (author, timestamp) from git log
- Handle telemetry API failures gracefully (don't block commits)
- Add tests verifying telemetry association called with correct parameters
- Update Phase F to accept TelemetryService instance

**Allowed paths:**
- `src/pipeline/orchestrator.py` - add TelemetryService.associate_commit() call in Phase F
- `src/cli/main.py` - pass TelemetryService to orchestrator
- `tests/test_commit_message_generation.py` - new test file (renamed to test_phase_f_telemetry_integration.py)

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m src.cli.main run --family zip` with git enabled
- Run `git log -1` to get commit SHA
- Verify telemetry API received commit association:
  ```bash
  curl "http://localhost:8765/api/v1/runs?limit=1" | jq '.[0].git_commit_hash'
  # Should show commit SHA from Phase F
  ```
- Verify commit metadata sent correctly:
  ```bash
  curl "http://localhost:8765/api/v1/runs/{run_id}" | jq '.git_commit_source'
  # Should show "llm"
  ```

**UI/Web/API:**
- N/A (CLI-only feature)
- Telemetry API: Verify `POST /api/v1/runs/{event_id}/associate-commit` called by Phase F
- Verify schema: `{"commit_hash": "abc123...", "commit_source": "llm", "commit_author": "...", "commit_timestamp": "..."}`

**Tests:**
- `pytest tests/test_phase_f_telemetry_integration.py -v` passes
- Test Phase F calls `TelemetryService.associate_commit()` after successful commit
- Test commit metadata extracted correctly from git log
- Test telemetry API failure doesn't crash Phase F
- Test commit association skipped when telemetry disabled
- Test commit_source="llm" sent correctly

**Config respected end-to-end:**
- Telemetry API integration optional (works without API configured)
- Commit association gracefully skipped when telemetry disabled

**No mock data in production paths:**
- Real git commits from Phase F
- Mock TelemetryService calls in tests

### Deliverables

1. **Updated `src/pipeline/orchestrator.py` - add telemetry association to Phase F:**
   - Accept `telemetry_service: Optional[TelemetryService]` parameter in `__init__()`:
     ```python
     def __init__(
         self,
         db: Database,
         global_config: Config,
         family_configs: Dict[str, Dict[str, Any]],
         telemetry_service: Optional[TelemetryService] = None,  # NEW
         ...
     ):
         self.telemetry_service = telemetry_service
     ```
   - After successful commit in Phase F (after line 1334), add telemetry association:
     ```python
     # Line 1334: commit_hash = commit_result.stdout.strip()
     logger.info(f"Created commit: {commit_hash}")

     # NEW: Associate commit with telemetry if service available
     if self.telemetry_service and run_id:
         try:
             # Extract commit metadata from git
             author_result = subprocess.run(
                 ['git', 'log', '-1', '--format=%an <%ae>', commit_hash],
                 capture_output=True, text=True, check=True, cwd=git_root
             )
             commit_author = author_result.stdout.strip()

             timestamp_result = subprocess.run(
                 ['git', 'log', '-1', '--format=%aI', commit_hash],
                 capture_output=True, text=True, check=True, cwd=git_root
             )
             commit_timestamp = timestamp_result.stdout.strip()

             # Call existing TelemetryService.associate_commit()
             self.telemetry_service.associate_commit(
                 event_id=run_id,
                 commit_hash=commit_hash,
                 commit_source="llm",  # LLM-generated commit
                 commit_author=commit_author,
                 commit_timestamp=commit_timestamp
             )
             logger.info(f"Associated commit {commit_hash} with telemetry run {run_id}")
         except Exception as e:
             # Don't crash Phase F on telemetry failure
             logger.warning(f"Failed to associate commit with telemetry: {e}")
     ```

2. **Updated `src/cli/main.py` - pass TelemetryService to orchestrator:**
   - Initialize TelemetryService and pass to Orchestrator:
     ```python
     # Initialize telemetry service if configured
     from src.services.telemetry_service import TelemetryService
     telemetry_service = None
     if global_config.telemetry.enabled:
         telemetry_service = TelemetryService(
             config=global_config.telemetry,
             db=db
         )

     # Create orchestrator with telemetry service
     orchestrator = Orchestrator(
         db=db,
         global_config=global_config,
         family_configs=family_configs,
         telemetry_service=telemetry_service,  # NEW: Pass telemetry service
         ...
     )
     ```

3. **New test file `tests/test_phase_f_telemetry_integration.py`:**
   - `test_phase_f_calls_associate_commit_after_git_commit`
   - `test_commit_metadata_extracted_correctly`
   - `test_commit_source_is_llm`
   - `test_telemetry_api_failure_doesnt_crash_phase_f`
   - `test_commit_association_skipped_when_telemetry_disabled`
   - `test_commit_hash_sent_correctly`

4. **Forward-compatible migration:**
   - Telemetry integration optional (Phase F works without telemetry service)
   - Existing Phase F git behavior unchanged
   - TelemetryService.associate_commit() method already exists (no changes needed)

### Hard Rules

- ✅ Keep public signatures: Add optional `telemetry_client` parameter with default None
- ✅ No network in offline tests: Mock telemetry API calls
- ✅ Deterministic runs: Commit messages deterministic for same input
- ✅ No new deps: Use existing libraries
- ✅ Keep code/docs/tests in sync: Document telemetry integration; reference docs/local-telemetry.md

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Commit messages accurate; telemetry API called correctly; schema compliant with docs/local-telemetry.md |
| **Completeness** | Includes patch count, file count, snippet IDs; telemetry integration works; commit_source=llm sent |
| **Robustness** | Handles long file lists; telemetry API failures don't block commits; graceful degradation |
| **Testability** | Tests verify message format; tests verify telemetry API integration; tests verify failure handling |
| **Documentation** | Docstrings explain message format and telemetry integration; references API spec |
| **Integration** | Works with AC-01/AC-02; enhances user experience; provides commit traceability via telemetry |

### Now (Runbook)

```bash
# 0. Read telemetry API documentation for commit association
cat docs/local-telemetry.md | grep -A 30 "associate-commit"
# Note the endpoint: POST /api/v1/runs/{event_id}/associate-commit
# Note the schema: commit_hash (7-40 chars), commit_source (manual/llm/ci), commit_author, commit_timestamp

# 1. Read existing _git_commit_changes() method
grep -A 30 "_git_commit_changes" src/patching_service.py

# 2. Implement _generate_commit_message() helper
# Add detailed commit message generation with conventional commit format

# 3. Implement _associate_commit_with_telemetry() method
# Add after _git_commit_changes()

# 4. Update src/telemetry.py with associate_commit() method
# Implement POST /api/v1/runs/{event_id}/associate-commit

# 5. Update PatchingService.__init__() to accept telemetry_client
# Add optional parameter: telemetry_client: Optional[TelemetryClient] = None

# 6. Update src/cli.py to pass telemetry_client to PatchingService
# Add: patcher = PatchingService(..., telemetry_client=telemetry)

# 7. Create test file
# Test commit message generation and telemetry API integration

# 8. Run tests with mocked telemetry API
pytest test_commit_message_generation.py -v

# 9. Integration test with real telemetry API
export TELEMETRY_API_URL=http://localhost:8765
python src/cli.py patch --family zip --auto-commit --max-snippets 3

# 10. Verify commit message format
git log -1 --format="%s%n%n%b"

# 11. Verify telemetry API received commit association
curl "http://localhost:8765/api/v1/runs?agent_name=example-reviewer&limit=1" | jq '.[0] | {git_commit_hash, git_commit_source, git_commit_author}'

# 12. Verify commit URL generated
curl "http://localhost:8765/api/v1/runs/{event_id}/commit-url"
```

---

## Taskcard AC-04: Add Rollback Mechanism

✅ **VALIDATED** - This is a genuinely new feature. Phase F has no rollback mechanism (Reality Check confirmed).

**Status:** Not Started

**Gap Linkage:** Fixes AC-GAP-05 (No rollback mechanism - manual git reset required)

**Role:** Senior engineer delivering production-ready rollback functionality for Phase F git commits.

---

### ⚠️ NOTE: This is a New Feature, Not a Fix

**Current Reality**:
- Phase F creates git commits but provides no rollback mechanism
- Users must manually run `git reset --hard` to undo automated commits
- No safety net for reviewing commits before they're pushed

**Work is to ADD**:
1. CLI command `python -m src.cli.main rollback` to undo Phase F commits
2. Rollback metadata storage in SQLite database
3. Safety checks: confirmation prompts, diff previews
4. Selective file rollback support

---

### Scope

**Fix:**
- Add `rollback` CLI command to `src/cli/main.py` to undo Phase F git commits
- Store rollback metadata (commit SHA, modified files, timestamp) in SQLite database
- Implement `git reset --hard` rollback to previous commit
- Implement selective file rollback (checkout specific files from previous commit)
- Add safety checks: confirm before rollback, show diff preview
- Support `--list` flag to show rollback history

**Allowed paths:**
- `src/cli/main.py` - add rollback command
- `src/core/database.py` - add rollback metadata storage
- `src/pipeline/orchestrator.py` - store rollback metadata after Phase F commit
- `schema.sql` - add rollback_history table (if needed)
- `tests/test_patching_rollback.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m src.cli.main run --family zip` (with git enabled) to create Phase F commit
- Capture commit SHA from Phase F output
- Run `python -m src.cli.main rollback --last` to undo Phase F commit
- Verify files restored to previous state
- Run `git log` to verify rollback (should show previous commit as HEAD)
- Run `python -m src.cli.main rollback --list` to see rollback history
- Run `python -m src.cli.main rollback --file test-content/zip/example.md` for selective rollback

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_patching_rollback.py -v` passes
- Test happy path: rollback restores files to previous state after Phase F commit
- Test selective rollback: only specified file restored
- Test rollback history: list shows previous Phase F commits
- Test safety: rollback requires confirmation (unless --force)
- Test edge case: rollback with no previous commit shows error
- Test edge case: rollback metadata stored correctly after Phase F commit

**Config respected end-to-end:**
- Rollback works for any Phase F git commit
- Rollback metadata stored in database automatically

**No mock data in production paths:**
- Real git operations (branch, reset, checkout)
- Mock git operations in tests

### Deliverables

1. **Updated `src/cli/main.py` - add `rollback` command:**
   ```python
   def rollback(args):
       """Rollback Phase F git commit operation."""
       from src.core.database import Database

       db = Database(args.db_path)

       if args.list:
           # Show rollback history from database
           history = db.get_rollback_history()
           for entry in history:
               print(f"{entry['timestamp']}: {entry['commit_sha'][:8]} - {entry['description']}")
       elif args.last:
           # Rollback last Phase F commit
           if not args.force:
               confirm = input("Are you sure you want to rollback the last commit? (y/N): ")
               if confirm.lower() != 'y':
                   print("Rollback cancelled.")
                   return
           rollback_last_commit(db, git_root=Path.cwd())
       elif args.file:
           # Selective file rollback
           rollback_file(db, args.file, git_root=Path.cwd())

   # Add to CLI parser
   parser_rollback = subparsers.add_parser('rollback', help='Rollback Phase F git commits')
   parser_rollback.add_argument('--last', action='store_true', help='Rollback last Phase F commit')
   parser_rollback.add_argument('--list', action='store_true', help='List rollback history')
   parser_rollback.add_argument('--file', type=str, help='Rollback specific file')
   parser_rollback.add_argument('--force', action='store_true', help='Skip confirmation')
   parser_rollback.set_defaults(func=rollback)
   ```

2. **Updated `src/core/database.py` - add rollback metadata storage:**
   - Add methods:
     - `save_rollback_metadata(commit_sha, family, modified_files)` - called by Phase F after commit
     - `get_rollback_history()` - retrieves history for `--list` command
     - `get_last_rollback_entry()` - retrieves last commit for rollback

3. **Updated `src/pipeline/orchestrator.py` - store rollback metadata after Phase F commit:**
   ```python
   # After line 1334 (commit_hash captured)
   # Store rollback metadata in database
   self.db.save_rollback_metadata(
       commit_sha=commit_hash,
       family=family,
       modified_files=touched_files,  # List of files in commit
       description=f"Phase F commit for {family} family"
   )
   ```

4. **Updated `schema.sql` (if needed):**
   ```sql
   CREATE TABLE IF NOT EXISTS rollback_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp TEXT NOT NULL,
       commit_sha TEXT NOT NULL,
       family TEXT,
       description TEXT,
       modified_files TEXT  -- JSON array of file paths
   );
   ```

5. **New test file `tests/test_patching_rollback.py`:**
   - `test_rollback_restores_previous_state`
   - `test_selective_file_rollback`
   - `test_rollback_history_listing`
   - `test_rollback_metadata_stored_after_phase_f`
   - `test_rollback_requires_confirmation`
   - `test_rollback_with_no_history_shows_error`

6. **Forward-compatible migration:**
   - Rollback command optional (doesn't affect normal Phase F workflow)
   - Rollback metadata automatically stored by Phase F when git commits happen

### Hard Rules

- ✅ Keep public signatures: New CLI command, doesn't affect existing commands
- ✅ No network in offline tests: Git operations are local
- ✅ Deterministic runs: Backup branch names include timestamp
- ✅ No new deps: Use built-in subprocess module

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Rollback restores exact previous state; metadata stored correctly; git operations succeed |
| **Completeness** | Full rollback, selective rollback, history listing all work; backup creation works |
| **Robustness** | Confirms before destructive operations; handles no history gracefully; validates git state |
| **Testability** | Tests verify rollback correctness; tests verify safety checks; tests cover edge cases |
| **Documentation** | Docstrings explain rollback workflow; CLI help text clear; safety warnings present |
| **Integration** | Works seamlessly with auto-commit; optional feature doesn't interfere with normal workflow |

### Now (Runbook)

```bash
# 1-12. Similar to previous version, implement rollback functionality
# See full implementation details in original taskcard
```

---

## Summary

**4 Taskcards Created:**
- **AC-01:** Implement auto-commit core functionality → Fixes git commit/staging automation, returns commit SHA
- **AC-02:** Add auto-commit configuration → Enables flexible config (CLI flag > family config > env var)
- **AC-03:** Implement smart commit message generation + **telemetry API integration** → Creates detailed conventional commits, associates commits with telemetry runs via `POST /api/v1/runs/{event_id}/associate-commit`
- **AC-04:** Add rollback mechanism → Provides safety net for patching operations

**Priority Order:**
1. **AC-01** (Critical - core functionality for auto-commit)
2. **AC-02** (High - makes auto-commit configurable and practical)
3. **AC-03** (High - enhances UX with good commit messages + telemetry traceability)
4. **AC-04** (Medium - safety feature, nice-to-have)

**Key Integration Points:**
- **AC-03** integrates with telemetry API v2.1.0 (see `docs/local-telemetry.md`)
- Commit association endpoint: `POST /api/v1/runs/{event_id}/associate-commit`
- Commit metadata tracked: `commit_hash`, `commit_source=llm`, `commit_author`, `commit_timestamp`
- Telemetry integration optional (graceful degradation if API not configured)
- Commit SHA captured in AC-01 enables telemetry integration in AC-03

**Telemetry API Schema (docs/local-telemetry.md lines 351-363):**
```json
{
  "commit_hash": "abc1234567890abcdef",
  "commit_source": "llm",
  "commit_author": "Claude Code <noreply@anthropic.com>",
  "commit_timestamp": "2026-01-02T10:00:00Z"
}
```

**Total Estimated Effort:** 2-3 days for all taskcards (AC-01: 6h, AC-02: 4h, AC-03: 6h, AC-04: 8h)

**Dependencies:**
- AC-02 depends on AC-01 (configuration requires core functionality)
- AC-03 depends on AC-01 (message generation enhances core functionality, uses commit SHA from AC-01)
- AC-03 integrates with TM-02 (telemetry API configuration required for commit association)
- AC-04 depends on AC-01 (rollback works with auto-committed changes)

**Risk Assessment:**
- **Low Risk:** AC-01, AC-02, AC-03 (non-destructive, opt-in features; telemetry failures don't block commits)
- **Medium Risk:** AC-04 (destructive operations, requires careful testing)
