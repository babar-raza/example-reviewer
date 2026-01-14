# Auto-Commit of Touched Files Healing Plan

## Context
File patching infrastructure is fully functional (tracks modified files, writes patches, supports dry-run), but git integration is completely missing. Users must manually run `git add` and `git commit` after patching operations. This creates friction and risk of forgetting to commit verified changes.

**Telemetry Integration:** Git commits should be associated with telemetry runs via the local-telemetry-api v2.1.0 endpoint `POST /api/v1/runs/{event_id}/associate-commit` (see `docs/local-telemetry.md` lines 695-719).

**Reference:** See [docs/local-telemetry.md](../docs/local-telemetry.md) for git commit tracking API

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) |
|----------------|-------------|----------------|
| AC-GAP-01 | No git commit automation - manual git commands required | AC-01 |
| AC-GAP-02 | No git staging (git add) automation - files not tracked | AC-01 |
| AC-GAP-03 | No configuration for auto-commit behavior - always manual | AC-02 |
| AC-GAP-04 | No git commit message generation - user must craft messages | AC-03 |
| AC-GAP-05 | No rollback mechanism - manual git reset required | AC-04 |
| AC-GAP-06 | No telemetry API commit association - commits not tracked in telemetry | AC-03 |

---

## Taskcard AC-01: Implement Auto-Commit Core Functionality

**Status:** Not Started

**Gap Linkage:** Fixes AC-GAP-01 (No git commit automation), AC-GAP-02 (No git staging)

**Role:** Senior engineer delivering drop-in, production-ready auto-commit functionality for patching operations.

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

1. **Updated `src/patching_service.py`:**
   - Add `auto_commit: bool = False` parameter to `patch_verified_snippets()`
   - After patching completes successfully (no errors), check if `auto_commit` and `modified_files`:
     ```python
     if auto_commit and results['modified_files'] and results['errors'] == 0 and not dry_run:
         commit_sha = self._git_commit_changes(results['modified_files'], results, family)
         results['commit_sha'] = commit_sha  # Store for telemetry integration
     ```
   - Implement `_git_commit_changes()` private method:
     ```python
     def _git_commit_changes(self, modified_files: set, results: dict, family: str) -> str:
         """Stage and commit modified files. Returns commit SHA."""
         import subprocess

         # 1. Check git available
         subprocess.run(['git', '--version'], check=True, capture_output=True)

         # 2. Stage files
         subprocess.run(['git', 'add'] + list(modified_files), check=True, cwd=self.content_root)

         # 3. Generate commit message (basic for now, enhanced in AC-03)
         message = f"Apply {results['patches_applied']} verified patches to {family} family"

         # 4. Commit
         subprocess.run(['git', 'commit', '-m', message], check=True, cwd=self.content_root)

         # 5. Get commit SHA
         result = subprocess.run(['git', 'rev-parse', 'HEAD'],
                                  capture_output=True, text=True, check=True, cwd=self.content_root)
         commit_sha = result.stdout.strip()

         print(f"Created git commit: {commit_sha}")
         return commit_sha
     ```
   - Error handling: catch `subprocess.CalledProcessError`, log warning, don't crash

2. **Updated `src/cli.py`:**
   - Add `--auto-commit` flag to `patch` command:
     ```python
     parser.add_argument('--auto-commit', action='store_true',
                         help='Automatically commit patched files to git')
     ```
   - Pass flag to PatchingService:
     ```python
     results = patcher.patch_verified_snippets(
         family=family,
         dry_run=args.dry_run,
         auto_commit=args.auto_commit,
         ...
     )

     # Log commit SHA if auto-commit succeeded
     if 'commit_sha' in results:
         print(f"Auto-commit created: {results['commit_sha']}")
     ```

3. **New test file `test_patching_auto_commit.py`:**
   - Use temporary git repository for tests (initialize with `git init`)
   - Test class `TestPatchingAutoCommit`:
     - `test_auto_commit_creates_commit`
     - `test_auto_commit_returns_commit_sha`
     - `test_auto_commit_stages_all_modified_files`
     - `test_dry_run_disables_auto_commit`
     - `test_auto_commit_skipped_on_errors`
     - `test_auto_commit_skipped_when_no_files_modified`
     - `test_git_not_available_graceful_error`
   - Mock subprocess calls or use real git in temp directory
   - Verify git log shows commit after patching
   - Verify commit SHA is valid 40-character hex string

4. **Forward-compatible migration:**
   - Existing CLI calls without `--auto-commit` flag behave exactly as before
   - New parameter `auto_commit` has safe default (`False`)
   - Commit SHA stored in results dict for optional telemetry integration (AC-03)

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
# 1. Read existing patching service
grep -A 50 "def patch_verified_snippets" src/patching_service.py

# 2. Add auto_commit parameter to patch_verified_snippets()
# Add: auto_commit: bool = False

# 3. Implement _git_commit_changes() method
# Add after existing helper methods around line 1100
# Must return commit SHA for telemetry integration

# 4. Call _git_commit_changes() at end of patch_verified_snippets()
# Add before return statement:
#   if auto_commit and results['modified_files'] and results['errors'] == 0 and not dry_run:
#       commit_sha = self._git_commit_changes(results['modified_files'], results, family)
#       results['commit_sha'] = commit_sha

# 5. Update CLI patch command
grep -A 20 "def patch" src/cli.py
# Add --auto-commit flag to parser.add_argument()

# 6. Pass auto_commit to patching service and log commit SHA
# Update call: patcher.patch_verified_snippets(..., auto_commit=args.auto_commit)
# Log: if 'commit_sha' in results: print(f"Auto-commit: {results['commit_sha']}")

# 7. Create test file
cat > test_patching_auto_commit.py << 'EOF'
import pytest
import tempfile
import subprocess
from pathlib import Path
from src.patching_service import PatchingService

@pytest.fixture
def temp_git_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        subprocess.run(['git', 'init'], cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, check=True)
        yield repo_path

# Tests...
EOF

# 8. Implement tests
# Test cases: auto-commit creates commit, returns SHA, dry-run disables, errors skip, etc.

# 9. Run tests
pytest test_patching_auto_commit.py -v

# 10. Integration test with real CLI
# Initialize temp git repo
cd /tmp/test-auto-commit
git init
git config user.name "Test User"
git config user.email "test@example.com"

# Run patch with auto-commit
python src/cli.py patch --family zip --auto-commit

# Verify commit created
git log -1

# Verify commit SHA captured
git log -1 --format=%H

# Verify all modified files staged and committed
git status  # Should show: nothing to commit, working tree clean
```

---

## Taskcard AC-02: Add Auto-Commit Configuration

**Status:** Not Started

**Gap Linkage:** Fixes AC-GAP-03 (No configuration for auto-commit behavior)

**Role:** Senior engineer delivering production-ready configuration system for auto-commit.

### Scope

**Fix:**
- Add `auto_commit` boolean to family configuration files (`config/families/*.json`)
- Read `auto_commit` config in CLI and apply as default (can be overridden by CLI flag)
- Add environment variable `AUTO_COMMIT_ENABLED` for global default
- Support three-level configuration hierarchy: CLI flag > family config > environment variable > default (False)
- Add validation: warn if auto-commit enabled but git not available

**Allowed paths:**
- `src/cli.py` - read config and environment variable
- `config/families/zip.json` - example configuration
- `.env.example` - document AUTO_COMMIT_ENABLED
- `test_auto_commit_config.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add `"auto_commit": true` to `config/families/zip.json`
- Run `python src/cli.py patch --family zip` (without --auto-commit flag)
- Verify git commit created (config enables it)
- Run `python src/cli.py patch --family zip --no-auto-commit` (new flag to disable)
- Verify no git commit created (CLI flag overrides config)
- Run `export AUTO_COMMIT_ENABLED=true && python src/cli.py patch --family pdf`
- Verify git commit created if pdf config doesn't disable it

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest test_auto_commit_config.py -v` passes
- Test family config enables auto-commit
- Test CLI flag overrides family config
- Test environment variable used as fallback
- Test hierarchy: CLI flag > family config > env var > default

**Config respected end-to-end:**
- All three configuration levels work correctly
- CLI flag has highest precedence
- Default remains False (opt-in, not opt-out)

**No mock data in production paths:**
- Real config files used in production
- Mock config files in tests

### Deliverables

1. **Updated `src/cli.py`:**
   - Read family config: `family_config.get('auto_commit', False)`
   - Read environment variable: `os.getenv('AUTO_COMMIT_ENABLED', 'false').lower() == 'true'`
   - Determine effective auto_commit:
     ```python
     # CLI flag > family config > env var > default
     if args.auto_commit is not None:  # Explicitly set via --auto-commit or --no-auto-commit
         auto_commit = args.auto_commit
     elif 'auto_commit' in family_config:
         auto_commit = family_config['auto_commit']
     else:
         auto_commit = os.getenv('AUTO_COMMIT_ENABLED', 'false').lower() == 'true'
     ```
   - Add `--no-auto-commit` flag to explicitly disable:
     ```python
     parser.add_argument('--auto-commit', action='store_true', default=None, dest='auto_commit')
     parser.add_argument('--no-auto-commit', action='store_false', dest='auto_commit')
     ```

2. **Updated `config/families/zip.json`:**
   - Add optional field:
     ```json
     {
       "family": "zip",
       "auto_commit": false,
       ...
     }
     ```
   - Document in comments: `// auto_commit: Enable automatic git commits after patching (default: false)`

3. **Updated `.env.example`:**
   ```
   # Optional: Enable auto-commit by default for all families (default: false)
   AUTO_COMMIT_ENABLED=false
   ```

4. **New test file `test_auto_commit_config.py`:**
   - `test_family_config_enables_auto_commit`
   - `test_cli_flag_overrides_family_config`
   - `test_env_var_used_as_fallback`
   - `test_config_hierarchy_correct`
   - `test_default_is_false_opt_in`
   - `test_no_auto_commit_flag_disables`

5. **Forward-compatible migration:**
   - Existing family configs without `auto_commit` field work (default False)
   - Existing CLI calls without flags work unchanged

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

## Taskcard AC-03: Implement Smart Commit Message Generation with Telemetry Integration

**Status:** Not Started

**Gap Linkage:** Fixes AC-GAP-04 (No git commit message generation), AC-GAP-06 (No telemetry API commit association)

**Role:** Senior engineer delivering intelligent commit message generation and telemetry API integration for commit tracking.

### Scope

**Fix:**
- Generate detailed commit messages with patch statistics
- Include family name, patch count, file count, error count
- List modified files in commit body (up to 10, then summarize)
- Add snippet IDs and issue types to commit message
- Support custom commit message template via config
- Follow conventional commit format (e.g., `fix:`, `chore:`, `docs:`)
- **NEW:** Integrate with telemetry API v2.1.0 endpoint `POST /api/v1/runs/{event_id}/associate-commit`
- **NEW:** Send commit metadata to telemetry API: commit_hash, commit_source=llm, commit_author, commit_timestamp
- **NEW:** Include commit SHA in telemetry metrics for traceability

**Allowed paths:**
- `src/patching_service.py` - enhance _git_commit_changes() method, add telemetry integration
- `src/cli.py` - pass telemetry client to patching service
- `config/families/zip.json` - example commit message template
- `test_commit_message_generation.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python src/cli.py patch --family zip --auto-commit`
- Run `git log -1 --format="%s%n%n%b"` to see commit message
- Verify message format (conventional commit with details)
- If telemetry API configured (`TELEMETRY_API_URL` set), verify commit associated:
  ```bash
  curl "http://localhost:8765/api/v1/runs?agent_name=example-reviewer&limit=1" | jq '.[0].git_commit_hash'
  # Should show commit SHA
  ```

**UI/Web/API:**
- N/A (CLI-only feature)
- Telemetry API: Verify `POST /api/v1/runs/{event_id}/associate-commit` called with correct schema

**Tests:**
- `pytest test_commit_message_generation.py -v` passes
- Test commit message includes patch count, file count
- Test commit message lists modified files (up to 10)
- Test commit message truncates file list when >10 files
- Test commit message includes snippet IDs
- Test custom commit message template from config
- **NEW:** Test telemetry API commit association called (mocked)
- **NEW:** Test commit metadata sent: commit_hash, commit_source, commit_author, commit_timestamp
- **NEW:** Test telemetry API failure doesn't block commit

**Config respected end-to-end:**
- Default commit message template used when not configured
- Custom template from family config overrides default
- Telemetry API integration optional (works without API configured)

**No mock data in production paths:**
- Real patch results used for commit messages
- Mock patch results and HTTP API in tests

### Deliverables

1. **Updated `src/patching_service.py`:**
   - Accept `telemetry_client: Optional[TelemetryClient] = None` parameter in `__init__()`
   - Enhance `_generate_commit_message()` method:
     ```python
     def _generate_commit_message(self, modified_files: set, results: dict, family: str) -> str:
         """Generate detailed commit message for patched files."""
         patch_count = results['patches_applied']
         file_count = len(modified_files)

         # Commit subject (conventional commit format)
         subject = f"fix({family}): apply {patch_count} verified patches to {file_count} file(s)"

         # Commit body with statistics and file list
         body_parts = [
             "",
             "Applied verified code patches from validation:",
             self._summarize_fixes(results['patches']),
             "",
             "Modified files:",
         ]

         # Add file list (truncate if >10)
         file_list = sorted(modified_files)
         if len(file_list) <= 10:
             body_parts.extend([f"- {fp}" for fp in file_list])
         else:
             body_parts.extend([f"- {fp}" for fp in file_list[:10]])
             body_parts.append(f"... and {len(file_list) - 10} more files")

         # Add snippet IDs
         snippet_ids = [p.get('snippet_id') for p in results['patches'] if p.get('success')]
         if snippet_ids:
             body_parts.append("")
             body_parts.append(f"Snippets: {', '.join(f'#{sid}' for sid in snippet_ids)}")

         return subject + '\n'.join(body_parts)
     ```
   - **NEW:** Implement `_associate_commit_with_telemetry()` method:
     ```python
     def _associate_commit_with_telemetry(self, commit_sha: str) -> None:
         """Associate git commit with telemetry run via API."""
         if not self.telemetry_client or not self.telemetry_client.event_id:
             return  # Telemetry not configured

         from datetime import datetime, timezone
         import subprocess

         try:
             # Get commit author and timestamp from git
             result = subprocess.run(
                 ['git', 'log', '-1', '--format=%an <%ae>%n%aI', commit_sha],
                 capture_output=True, text=True, check=True, cwd=self.content_root
             )
             lines = result.stdout.strip().split('\n')
             commit_author = lines[0] if len(lines) > 0 else "Unknown <unknown@example.com>"
             commit_timestamp = lines[1] if len(lines) > 1 else datetime.now(timezone.utc).isoformat()

             # Send to telemetry API
             self.telemetry_client.associate_commit(
                 commit_hash=commit_sha,
                 commit_source="llm",  # LLM-generated commit (example-reviewer)
                 commit_author=commit_author,
                 commit_timestamp=commit_timestamp
             )
             print(f"Associated commit {commit_sha} with telemetry run")
         except Exception as e:
             # Don't crash on telemetry failure
             print(f"Warning: Failed to associate commit with telemetry: {e}")
     ```
   - Update `_git_commit_changes()` to call telemetry integration:
     ```python
     commit_sha = result.stdout.strip()
     print(f"Created git commit: {commit_sha}")

     # Associate with telemetry if configured
     self._associate_commit_with_telemetry(commit_sha)

     return commit_sha
     ```

2. **NEW: Updated `src/telemetry.py`:**
   - Implement `associate_commit()` method:
     ```python
     def associate_commit(self, commit_hash: str, commit_source: str,
                          commit_author: str, commit_timestamp: str) -> None:
         """Associate git commit with telemetry run via API.

         Calls POST /api/v1/runs/{event_id}/associate-commit per docs/local-telemetry.md.

         Args:
             commit_hash: Git commit SHA (7-40 characters)
             commit_source: One of: manual, llm, ci
             commit_author: Commit author (e.g., "Name <email>")
             commit_timestamp: ISO8601 timestamp with timezone
         """
         if not self.telemetry_url or not self.event_id:
             return  # Telemetry API not configured

         try:
             import requests

             url = f"{self.telemetry_url}/api/v1/runs/{self.event_id}/associate-commit"
             payload = {
                 "commit_hash": commit_hash,
                 "commit_source": commit_source,
                 "commit_author": commit_author,
                 "commit_timestamp": commit_timestamp
             }

             headers = {"Content-Type": "application/json"}
             if self.auth_enabled and self.auth_token:
                 headers["Authorization"] = f"Bearer {self.auth_token}"

             response = requests.post(url, json=payload, headers=headers,
                                       timeout=self.timeout_ms/1000.0)
             response.raise_for_status()

             # Log event to NDJSON
             self.log_event("commit_associated", "info",
                            f"Associated commit {commit_hash} with run",
                            {"commit_hash": commit_hash, "commit_source": commit_source})
         except Exception as e:
             # Log but don't crash
             self.log_event("commit_association_failed", "warning",
                            f"Failed to associate commit: {e}",
                            {"error": str(e)})
     ```

3. **Updated `src/cli.py`:**
   - Pass telemetry_client to PatchingService:
     ```python
     patcher = PatchingService(
         db=db,
         content_root=args.content_root,
         telemetry_client=telemetry  # Pass telemetry client
     )
     ```

4. **Updated `config/families/zip.json` (optional):**
   ```json
   {
     "family": "zip",
     "commit_message_template": "fix(zip): apply {patch_count} patches\n\n{file_list}\n\nSnippets: {snippet_ids}",
     ...
   }
   ```

5. **New test file `test_commit_message_generation.py`:**
   - `test_commit_message_includes_patch_count`
   - `test_commit_message_includes_file_count`
   - `test_commit_message_lists_files_up_to_10`
   - `test_commit_message_truncates_long_file_list`
   - `test_commit_message_includes_snippet_ids`
   - `test_commit_message_conventional_format`
   - **NEW:** `test_telemetry_api_associate_commit_called`
   - **NEW:** `test_commit_metadata_correct_schema`
   - **NEW:** `test_telemetry_api_failure_doesnt_block_commit`
   - **NEW:** `test_commit_source_is_llm`

6. **Forward-compatible migration:**
   - Telemetry integration optional (works without telemetry configured)
   - Existing auto-commit code enhanced with telemetry tracking

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

**Status:** Not Started

**Gap Linkage:** Fixes AC-GAP-05 (No rollback mechanism)

**Role:** Senior engineer delivering production-ready rollback functionality for patching operations.

### Scope

**Fix:**
- Add `--create-backup` flag to create git stash or branch before patching
- Add `rollback` CLI command to undo last patching operation
- Store rollback metadata (commit SHA, modified files) in SQLite database
- Implement `git reset --hard` rollback to previous commit
- Implement selective file rollback (checkout specific files)
- Add safety checks: confirm before rollback, show diff preview

**Allowed paths:**
- `src/cli.py` - add rollback command, --create-backup flag
- `src/patching_service.py` - store rollback metadata
- `src/database.py` - add rollback metadata table (if needed)
- `schema.sql` - add rollback_history table (if needed)
- `test_patching_rollback.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python src/cli.py patch --family zip --auto-commit --create-backup`
- Verify backup created (git branch or stash)
- Run `python src/cli.py rollback --last`
- Verify files restored to previous state
- Run `git log` to see rollback commit
- Run `python src/cli.py rollback --list` to see rollback history
- Run `python src/cli.py rollback --file content/blog.aspose.net/zip/create-zip/index.md` for selective rollback

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest test_patching_rollback.py -v` passes
- Test happy path: rollback restores files to previous state
- Test selective rollback: only specified file restored
- Test rollback history: list shows previous operations
- Test safety: rollback requires confirmation (unless --force)
- Test edge case: rollback with no previous operation shows error

**Config respected end-to-end:**
- Backup created only when `--create-backup` flag present
- Rollback works regardless of auto-commit setting

**No mock data in production paths:**
- Real git operations (branch, reset, checkout)
- Mock git operations in tests

### Deliverables

1. **Updated `src/cli.py` - add `rollback` command:**
   ```python
   def rollback(args):
       """Rollback patching operation."""
       from src.patching_service import PatchingService

       patcher = PatchingService(db=db, content_root=args.content_root)

       if args.list:
           # Show rollback history
           history = patcher.get_rollback_history()
           for entry in history:
               print(f"{entry['timestamp']}: {entry['description']}")
       elif args.last:
           # Rollback last operation
           if not args.force:
               confirm = input("Are you sure you want to rollback? (y/N): ")
               if confirm.lower() != 'y':
                   print("Rollback cancelled.")
                   return
           patcher.rollback_last_operation()
       elif args.file:
           # Selective file rollback
           patcher.rollback_file(args.file)

   # Add to CLI parser
   parser_rollback = subparsers.add_parser('rollback', help='Rollback patching operations')
   parser_rollback.add_argument('--last', action='store_true', help='Rollback last operation')
   parser_rollback.add_argument('--list', action='store_true', help='List rollback history')
   parser_rollback.add_argument('--file', type=str, help='Rollback specific file')
   parser_rollback.add_argument('--force', action='store_true', help='Skip confirmation')
   parser_rollback.set_defaults(func=rollback)
   ```

2. **Updated `src/cli.py` - add `--create-backup` flag:**
   ```python
   # In patch command
   parser_patch.add_argument('--create-backup', action='store_true',
                             help='Create git backup before patching')
   ```

3. **Updated `src/patching_service.py`:**
   - Implement `create_backup()`, `rollback_last_operation()`, `rollback_file()`, `get_rollback_history()` methods
   - Store rollback metadata in database

4. **Updated `schema.sql` (if needed):**
   ```sql
   CREATE TABLE IF NOT EXISTS rollback_history (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       timestamp TEXT NOT NULL,
       commit_sha TEXT NOT NULL,
       backup_branch TEXT,
       family TEXT,
       description TEXT,
       modified_files TEXT  -- JSON array of file paths
   );
   ```

5. **New test file `test_patching_rollback.py`:**
   - Test backup creation, rollback, selective rollback, history listing

6. **Forward-compatible migration:**
   - Rollback command optional (doesn't affect normal workflow)

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
