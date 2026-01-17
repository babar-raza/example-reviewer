# Infrastructure Hardening Healing Plan

## Context
**Critical Issues Identified in `reviews/chatgpt.md`:**

The pipeline has several infrastructure and alignment gaps that prevent out-of-the-box usage and create confusion between documentation, specs, and implementation:

1. **~~Missing Config Files~~**: ✅ **CORRECTION: Configs already exist in repository** - ChatGPT review was conducted without config/ directory uploaded, creating false gap
2. **CLI Entry Point Mismatch**: Documentation says `python -m cli` but actual is `python -m src.cli.main`
3. **Outdated Documentation**: `/docs/*.md` references old architecture (validation_orchestrator, patching_service, etc.) that no longer exists
4. **Empty Source Packages**: Several `src/*` packages contain only `__pycache__` without `.py` sources
5. **Repository Hygiene**: Need `.gitignore` rules, pycache cleanup, and artifact removal

**Business Impact:**
- ~~New users cannot run pipeline without manual config creation~~ **Configs already exist - no issue**
- Documentation misleads developers about system architecture
- Risk of import confusion from empty packages
- Repository appears unmaintained with cached artifacts

**Reference:** See `reviews/chatgpt.md` for detailed analysis

**IMPORTANT NOTE:** IH-GAP-01 (Missing Config Files) is NOT a real gap. The config/ directory exists in the repository but was not included in the ChatGPT review context. IH-01 taskcard is therefore NOT NEEDED.

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) | Status |
|----------------|-------------|----------------|--------|
| IH-GAP-01 | ~~No config/ directory shipped~~ | ~~IH-01~~ | ✅ **NOT NEEDED** - Configs exist |
| IH-GAP-02 | CLI entry point mismatch - docs wrong, breaks user workflows | IH-02 | ⚠️ Needs fixing |
| IH-GAP-03 | Outdated architecture docs - references non-existent files | IH-03 | ⚠️ Needs fixing |
| IH-GAP-04 | Empty source packages with __pycache__ only | IH-04 | ⚠️ Needs fixing |
| IH-GAP-05 | No .gitignore or repo hygiene rules | IH-04 | ⚠️ Needs fixing |

---

## Repo Reality Check

**Purpose**: Verify the plan's assumptions match the actual repository structure before implementation.

### Validation Commands

```bash
# 1. Verify CLI entry point
python -m src.cli.main --help  # Current working entry point
python -m cli --help 2>&1 | grep -q "No module" && echo "NEEDS FIX: cli module missing"

# 2. Check for empty packages with only __pycache__
find src/ -type d -name "__pycache__" | while read dir; do
    pkg=$(dirname "$dir")
    py_count=$(find "$pkg" -maxdepth 1 -name "*.py" | wc -l)
    if [ "$py_count" -eq 0 ]; then
        echo "EMPTY PACKAGE: $pkg"
    fi
done

# 3. Verify docs reference actual files
grep -h "src/.*\.py" docs/*.md 2>/dev/null | grep -oP "src/[^)\s']+" | sort -u | while read file; do
    [ ! -f "$file" ] && echo "MISSING: $file referenced in docs"
done

# 4. Check .gitignore status
[ ! -f .gitignore ] && echo "MISSING: .gitignore" || echo "OK: .gitignore exists"

# 5. List current entry points
ls -la src/cli/*.py
[ -d cli ] && ls -la cli/*.py || echo "MISSING: top-level cli/ package"
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| Config exists | ✅ CORRECT | `config/global.json`, `config/families/zip.json` present |
| CLI is `src.cli.main` | ✅ CORRECT | `src/cli/main.py` exists and works |
| Top-level `cli/` missing | ✅ CORRECT | No `cli/__main__.py` - needs creation |
| Empty packages exist | ⚠️ VERIFY | Need to check for packages with only `__pycache__` |
| Docs reference old files | ⚠️ VERIFY | `validation_orchestrator.py`, `patching_service.py` may be stale references |
| No .gitignore | ⚠️ VERIFY | Need to check if comprehensive .gitignore exists |

### Go/No-Go Decision

✅ **GO** - Plan is aligned with reality after IH-01 correction:
- IH-02: CLI entry point mismatch is real - needs `cli/__main__.py`
- IH-03: Doc drift is real - need to audit and update
- IH-04: Hygiene issues are real - need cleanup

**Estimated Reality Check Time**: 10 minutes

---

## Taskcard IH-01: Add Config Scaffolding

⚠️ **STATUS: NOT NEEDED** - This taskcard is OBSOLETE. The config/ directory already exists in the repository.

**Gap Linkage:** ~~Fixes IH-GAP-01 (Missing config/ directory)~~ - **Gap does not exist**

**Priority:** ~~🔥 **CRITICAL**~~ → ✅ **RESOLVED** - Configs already present

**Role:** ~~Senior engineer delivering production-ready configuration scaffolding for immediate usability.~~ **NOT APPLICABLE**

---

**IMPORTANT:** The ChatGPT review that identified this gap was conducted without the config/ directory being uploaded. The repository already contains:
- `config/global.json` - Global configuration with LLM, telemetry, vector DB, and all pipeline settings
- `config/families/zip.json` - Complete ZIP family configuration with NuGet, runtime validation, and API patterns

**This taskcard should be SKIPPED. No action required.**

---

### ~~Original Taskcard Details~~ (For Reference Only - DO NOT IMPLEMENT)

### Scope

**Fix:**
- Create `config/` directory structure
- Add `config/families/zip.json` with working configuration
- Add `config/global.json` with sensible defaults
- Validate configs load correctly on startup
- Document config schema and customization

**Allowed paths:**
- `config/families/zip.json` - NEW: working zip family config
- `config/global.json` - NEW: global defaults
- `config/README.md` - NEW: config documentation
- `src/core/config.py` - validation improvements
- `tests/test_config_loading.py` - config loading tests

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m src.cli.main run --family zip` without FileNotFoundError
- Verify config loads from `config/families/zip.json`
- Verify global config loads from `config/global.json`
- Run `python -m src.cli.main scan --family zip`
- See discovery phase complete successfully

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_config_loading.py -v` passes
- Test zip family config loads correctly
- Test global config loads correctly
- Test config validation catches malformed JSON
- Test missing config file provides helpful error

**Config respected end-to-end:**
- All pipeline phases use loaded config
- Config changes reflected in behavior

**No mock data in production paths:**
- Real config files in config/ directory
- Test configs in tests/fixtures/

### Deliverables

1. **NEW: `config/families/zip.json`:**
   ```json
   {
     "family": "zip",
     "display_name": "Aspose.ZIP for .NET",
     "auto_commit": false,
     "content_roots": [
       "test-reference/zip"
     ],
     "content_pattern": {
       "test": "**/*.md"
     },
     "nuget_config": {
       "primary_package": {
         "name": "Aspose.Zip",
         "version_strategy": "latest_stable"
       },
       "additional_packages": [],
       "target_frameworks": ["net8.0"]
     },
     "code_defaults": {
       "default_usings": [
         "System",
         "System.IO",
         "System.Text",
         "Aspose.Zip",
         "Aspose.Zip.Saving",
         "Aspose.Zip.SevenZip",
         "Aspose.Zip.Rar"
       ]
     },
     "patterns": [],
     "non_existent_apis": [
       "SaveAsync",
       "CreateEntryAsync",
       "ExtractAsync",
       "OpenAsync"
     ],
     "api_patterns": {
       "compression_basic": {
         "description": "Create archive with compression settings",
         "code": "var settings = new ArchiveEntrySettings(new DeflateCompressionSettings());\nusing (var archive = new Archive(settings)) {\n    archive.CreateEntry(\"file.txt\", \"source.txt\");\n    archive.Save(\"output.zip\");\n}"
       }
     },
     "runtime_validation": {
       "enabled": true,
       "mode": "lenient",
       "timeout_seconds": 30,
       "required_files": ["sample.zip", "archive.zip"],
       "file_aliases": {
         "sample.zip": ["input.zip", "example.zip", "source.zip"]
       },
       "expected_outputs": ["*.zip", "output/*.zip"],
       "env": {}
     },
     "test_data": {
       "local_path": "test-data/zip",
       "download_if_missing": false
     },
     "example_repo": {
       "url": "https://github.com/aspose-zip/Aspose.ZIP-for-.NET",
       "examples_path": "Examples",
       "test_data_path": "Data",
       "ref": "main"
     },
     "api_reference": {
       "sources": ["test-data/test-reference/zip"],
       "cache_path": "./cache/api-reference/zip"
     }
   }
   ```

2. **NEW: `config/global.json`:**
   ```json
   {
     "llm": {
       "provider": "ollama",
       "model": "qwen2.5:14b",
       "temperature": 0.2,
       "max_retries": 3,
       "retry_backoff_seconds": 5,
       "api_key_env_var": "OPENAI_API_KEY",
       "base_url": "http://localhost:11434/v1",
       "timeout_seconds": 120
     },
     "limits": {
       "cpu_max_percent": 90,
       "ram_max_mb": 0,
       "vram_max_mb": 0
     },
     "resource_detection": {
       "auto_detect_vram": true,
       "prefer_gpu_when_available": true,
       "fallback_to_cpu": true,
       "telemetry_log_resource_decisions": true
     },
     "git": {
       "enabled": false,
       "commit_message_template": "chore({family}): verify {count} examples",
       "commit_description_template": "Automated verification of {count} examples.\n\nRunId: {run_id}\nFamily: {family}",
       "only_commit_touched_files": true
     },
     "gist": {
       "enabled": false,
       "target_account": "aspose-com-gists",
       "auth": {
         "method": "none",
         "pat_env_var": "GIST_PAT"
       },
       "upload_mode": "inline-only",
       "is_public": true,
       "description_template": "Verified example from {family} - {file_path}"
     },
     "telemetry": {
       "internal_enabled": true,
       "local_telemetry_enabled": true,
       "local_telemetry_path": "./local-telemetry",
       "http_api_enabled": false,
       "http_api_url": "http://localhost:8765",
       "http_api_timeout_seconds": 10,
       "http_api_retry_count": 3
     },
     "vector_db": {
       "enabled": true,
       "provider": "chromadb",
       "embedding_model": "all-MiniLM-L6-v2",
       "persist_directory": "./data/chroma",
       "search_k": 3,
       "min_similarity_threshold": 0.7
     },
     "backfill": {
       "auto_enabled": false,
       "targets": ["test_data", "api_reference", "examples", "gist_source_code"],
       "github_timeout_seconds": 120,
       "retry_on_failure": true
     },
     "final_review": {
       "enabled": true,
       "auto_remediation_enabled": false,
       "max_review_attempts": 2,
       "strict_mode": false,
       "fail_on_critical": true
     },
     "artifact_store_path": "./artifacts",
     "database_path": "./data/example_reviewer.db"
   }
   ```

3. **NEW: `config/README.md`:**
   ```markdown
   # Configuration Guide

   ## Directory Structure

   ```
   config/
   ├── global.json           # Global pipeline settings
   ├── families/             # Per-family configurations
   │   ├── zip.json          # Aspose.ZIP family
   │   ├── pdf.json          # Aspose.PDF family (example)
   │   └── ...
   └── README.md             # This file
   ```

   ## Config Loading Order

   1. Load `global.json` (defaults for all families)
   2. Load `families/{family}.json` (family-specific overrides)
   3. Merge: family config overrides global config

   ## Family Config Schema

   See `zip.json` for a complete working example.

   ### Required Fields

   - `family` (str): Unique family identifier
   - `content_roots` (list): Markdown content directories
   - `nuget_config` (object): NuGet package configuration

   ### Optional Fields

   - `content_pattern` (object): Glob patterns for file discovery
   - `runtime_validation` (object): Runtime verification settings
   - `api_reference` (object): API documentation paths
   - `test_data` (object): Test data configuration

   ## Global Config Schema

   ### LLM Settings

   - `llm.provider`: "ollama", "openai", "azure"
   - `llm.model`: Model name (e.g., "qwen2.5:14b", "gpt-4o-mini")
   - `llm.temperature`: 0.0-1.0 (lower = more deterministic)

   ### Resource Limits

   - `limits.cpu_max_percent`: CPU usage limit (0 = no limit)
   - `limits.ram_max_mb`: RAM limit (0 = no limit)

   ### Git Integration

   - `git.enabled`: Enable automatic commits
   - `git.commit_message_template`: Template for commit messages

   ## Creating New Family Configs

   1. Copy `zip.json` to `families/{your-family}.json`
   2. Update `family`, `content_roots`, and `nuget_config`
   3. Customize `code_defaults.default_usings` for your API
   4. Test with: `python -m src.cli.main scan --family {your-family}`

   ## Validation

   Configs are validated on load. Common errors:

   - **Missing required fields**: Add required fields to family config
   - **Invalid JSON**: Check for trailing commas, missing quotes
   - **Invalid paths**: Ensure `content_roots` and paths exist
   - **Invalid enum values**: Check `provider`, `upload_mode`, etc.

   ## Environment Variables

   Some settings support environment variable overrides:

   - `OPENAI_API_KEY`: OpenAI API key (if using OpenAI provider)
   - `GIST_PAT`: GitHub Personal Access Token for gist uploads
   - `TELEMETRY_API_URL`: HTTP telemetry endpoint

   ## Examples

   ### Minimal Family Config

   ```json
   {
     "family": "minimal",
     "content_roots": ["content/"],
     "nuget_config": {
       "primary_package": {
         "name": "YourPackage",
         "version_strategy": "latest_stable"
       }
     }
   }
   ```

   ### Custom LLM Settings (Global)

   ```json
   {
     "llm": {
       "provider": "openai",
       "model": "gpt-4o-mini",
       "temperature": 0.1,
       "base_url": "https://api.openai.com/v1"
     }
   }
   ```
   ```

4. **Updated `src/core/config.py`:**
   - Improve error messages for missing configs
   - Add config validation on load
   - Log config loading success/failure

5. **New test file `tests/test_config_loading.py`:**
   - `test_zip_family_config_loads`
   - `test_global_config_loads`
   - `test_missing_config_file_error`
   - `test_invalid_json_error`
   - `test_family_config_overrides_global`
   - `test_config_validation_catches_errors`

6. **Forward-compatible migration:**
   - Existing code expects configs, now they're present
   - No breaking changes to config schema

### Hard Rules

- ✅ Keep public signatures: No changes to ConfigurationManager API
- ✅ Deterministic runs: Same config → same behavior
- ✅ No new deps: Standard library JSON only
- ✅ Keep code/docs/tests in sync: Config README documents schema

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Configs load correctly; validation works; sensible defaults |
| **Completeness** | All required fields present; README comprehensive; examples provided |
| **Robustness** | Helpful error messages; validates on load; catches common mistakes |
| **Testability** | Tests verify loading, validation, overrides |
| **Documentation** | README explains schema, loading order, customization |
| **Integration** | Pipeline runs immediately; no manual setup needed |

### Now (Runbook)

```bash
# 1. Create config directory structure
mkdir -p config/families

# 2. Create config/families/zip.json
# Copy content from deliverable #1

# 3. Create config/global.json
# Copy content from deliverable #2

# 4. Create config/README.md
# Copy content from deliverable #3

# 5. Update src/core/config.py error messages
# Improve FileNotFoundError message to mention config/families/

# 6. Create tests/test_config_loading.py
# Test config loading scenarios

# 7. Run tests
pytest tests/test_config_loading.py -v

# 8. Verify pipeline runs with new configs
python -m src.cli.main scan --family zip

# 9. Verify discovery phase completes
# Should see: "Processed N files for family zip"

# 10. Test missing config error message
mv config/families/zip.json config/families/zip.json.bak
python -m src.cli.main scan --family zip
# Should see helpful error message
mv config/families/zip.json.bak config/families/zip.json

# 11. Commit configs to repo
git add config/
git commit -m "feat: add config scaffolding for immediate usability"
```

---

## Taskcard IH-02: Fix CLI Entry Point Contract

**Status:** Not Started

**Gap Linkage:** Fixes IH-GAP-02 (CLI entry point mismatch)

**Priority:** 🔥 **HIGH** - User-facing breaking change

**Role:** Senior engineer delivering CLI contract alignment for consistent user experience.

### Scope

**Fix:**
- Create top-level `cli` package so `python -m cli` works
- Keep backward compatibility with `python -m src.cli.main`
- Update all documentation to use `python -m cli`
- Add CLI entry point to setup.py for `example-reviewer` command
- Provide migration guide for existing users

**Allowed paths:**
- `cli/__init__.py` - NEW: top-level CLI package
- `cli/__main__.py` - NEW: entry point
- `setup.py` - add CLI entry point
- `README.md` - update CLI examples
- `docs/*.md` - update CLI references
- `tests/test_cli_entry_point.py` - test both entry points work

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli run --family zip` - works
- Run `python -m src.cli.main run --family zip` - still works (backward compat)
- Run `example-reviewer run --family zip` - works (if installed)
- Verify both entry points behave identically

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_cli_entry_point.py -v` passes
- Test `python -m cli` works
- Test `python -m src.cli.main` works (backward compat)
- Test both entry points produce identical output

**Config respected end-to-end:**
- CLI entry point independent of configuration
- Both paths use same configuration loading

**No mock data in production paths:**
- Real CLI invocation
- Test CLI in subprocess tests

### Deliverables

1. **NEW: `cli/__init__.py`:**
   ```python
   """
   Top-level CLI package for Example Reviewer.

   This package provides the `python -m cli` entry point as an alias
   for the internal `src.cli.main` module.

   Usage:
       python -m cli run --family zip
       python -m cli scan --family zip
       python -m cli extract --family zip
   """

   __version__ = "0.1.0"
   ```

2. **NEW: `cli/__main__.py`:**
   ```python
   """
   Entry point for `python -m cli` invocation.

   This delegates to src.cli.main for backward compatibility while
   providing the user-facing contract documented in README.md.
   """

   import sys
   from src.cli.main import main

   if __name__ == "__main__":
       sys.exit(main())
   ```

3. **Updated `setup.py` (or create if missing):**
   ```python
   from setuptools import setup, find_packages

   setup(
       name="example-reviewer",
       version="0.1.0",
       packages=find_packages(),
       install_requires=[
           "pydantic>=2.0.0",
           "requests>=2.28.0",
           "sentence-transformers>=2.2.0",
           "chromadb>=0.4.0",
           "instructor>=0.4.0",
       ],
       entry_points={
           "console_scripts": [
               "example-reviewer=src.cli.main:main",
           ],
       },
       python_requires=">=3.9",
       description="Automated code example validation and review pipeline",
       author="Aspose",
       license="MIT",
   )
   ```

4. **Updated `README.md`:**
   ```markdown
   # Example Reviewer

   Automated code example validation and review pipeline.

   ## Installation

   ```bash
   # Development install
   pip install -e .

   # Or run directly
   python -m cli --help
   ```

   ## Quick Start

   ```bash
   # Discover code examples
   python -m cli scan --family zip

   # Extract and compile examples
   python -m cli extract --family zip

   # Run full pipeline
   python -m cli run --family zip
   ```

   ## CLI Commands

   - `scan` - Discover code examples in markdown (Phase A)
   - `extract` - Extract examples to database
   - `compile-verify` - Verify compilation (Phase B)
   - `runtime-verify` - Verify runtime execution (Phase C)
   - `md-update` - Update markdown with verified code (Phase D)
   - `final-review` - LLM review (Phase E)
   - `run` - Execute full pipeline (Phases A-F)

   ## Backward Compatibility

   The following invocations are equivalent:

   ```bash
   python -m cli run --family zip
   python -m src.cli.main run --family zip
   example-reviewer run --family zip  # if installed
   ```
   ```

5. **Updated `docs/*.md`:**
   - Replace all `python -m src.cli.main` with `python -m cli`
   - Add note about backward compatibility

6. **New test file `tests/test_cli_entry_point.py`:**
   ```python
   import subprocess
   import sys

   def test_cli_module_works():
       """Test that 'python -m cli' works."""
       result = subprocess.run(
           [sys.executable, "-m", "cli", "--help"],
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Example Reviewer" in result.stdout or "usage:" in result.stdout

   def test_src_cli_main_works_backward_compat():
       """Test that 'python -m src.cli.main' still works (backward compat)."""
       result = subprocess.run(
           [sys.executable, "-m", "src.cli.main", "--help"],
           capture_output=True,
           text=True
       )
       assert result.returncode == 0
       assert "Example Reviewer" in result.stdout or "usage:" in result.stdout

   def test_both_entry_points_identical():
       """Test that both entry points produce identical output."""
       result1 = subprocess.run(
           [sys.executable, "-m", "cli", "--help"],
           capture_output=True,
           text=True
       )

       result2 = subprocess.run(
           [sys.executable, "-m", "src.cli.main", "--help"],
           capture_output=True,
           text=True
       )

       assert result1.stdout == result2.stdout
       assert result1.returncode == result2.returncode
   ```

7. **Forward-compatible migration:**
   - Both `python -m cli` and `python -m src.cli.main` work
   - Existing scripts continue to work
   - New documentation uses `python -m cli`

### Hard Rules

- ✅ Keep public signatures: No changes to src.cli.main
- ✅ Backward compatible: Old entry point still works
- ✅ Deterministic runs: Both entry points identical behavior
- ✅ No new deps: Standard library only
- ✅ Keep code/docs/tests in sync: All docs updated

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Both entry points work; identical behavior; help text same |
| **Completeness** | All invocation methods work; docs updated; migration guide provided |
| **Robustness** | No import errors; graceful fallback; clear error messages |
| **Testability** | Tests verify both entry points; subprocess tests pass |
| **Documentation** | README clear; all docs updated; backward compat noted |
| **Integration** | Installed command works; development mode works; no breaking changes |

### Now (Runbook)

```bash
# 1. Create top-level cli package
mkdir cli
touch cli/__init__.py
touch cli/__main__.py

# 2. Implement cli/__main__.py
# Delegate to src.cli.main

# 3. Test new entry point
python -m cli --help

# 4. Test backward compatibility
python -m src.cli.main --help

# 5. Create/update setup.py
# Add console_scripts entry point

# 6. Test installed command (optional)
pip install -e .
example-reviewer --help

# 7. Update README.md
# Replace all CLI examples with `python -m cli`

# 8. Update all docs/*.md files
find docs -name "*.md" -exec sed -i 's/python -m src\.cli\.main/python -m cli/g' {} \;

# 9. Create test file tests/test_cli_entry_point.py
# Implement subprocess tests

# 10. Run tests
pytest tests/test_cli_entry_point.py -v

# 11. Verify both work identically
python -m cli scan --family zip --max-files 1
python -m src.cli.main scan --family zip --max-files 1

# 12. Commit changes
git add cli/ setup.py README.md docs/
git commit -m "feat: add top-level CLI entry point (python -m cli)"
```

---

## Taskcard IH-03: Align Architecture Documentation

**Status:** Not Started

**Gap Linkage:** Fixes IH-GAP-03 (Outdated architecture docs)

**Priority:** 🟡 **MEDIUM** - Documentation debt, misleads developers

**Role:** Senior engineer delivering accurate architecture documentation aligned with current implementation.

### Scope

**Fix:**
- Update `docs/architecture.md` to reflect current src/ layout
- Remove references to non-existent files (validation_orchestrator.py, patching_service.py, etc.)
- Update database schema documentation to match current schema
- Add architecture diagrams for current phase flow
- Document actual services in src/services/

**Allowed paths:**
- `docs/architecture.md` - complete rewrite
- `docs/database-schema.md` - NEW: current schema
- `docs/phase-flow.md` - NEW: phase orchestration
- `docs/services.md` - NEW: service catalog
- `docs/diagrams/` - NEW: architecture diagrams

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- N/A (documentation only)

**UI/Web/API:**
- N/A (documentation only)

**Tests:**
- No tests required (documentation)
- Manual review: docs match actual code

**Config respected end-to-end:**
- N/A (documentation only)

**No mock data in production paths:**
- N/A (documentation only)

### Deliverables

1. **Updated `docs/architecture.md`:**
   - Remove references to old architecture
   - Document current phase flow (A-F)
   - Document orchestrator pattern
   - List all src/services/ modules
   - Show data flow through pipeline

2. **NEW: `docs/database-schema.md`:**
   - Document all tables: example_records, compile_attempts, runtime_attempts, etc.
   - Show relationships and indexes
   - Explain status state machine

3. **NEW: `docs/phase-flow.md`:**
   - Detailed walkthrough of Phases A-F
   - Decision points and retry logic
   - LLM integration points
   - Vector DB usage

4. **NEW: `docs/services.md`:**
   - DiscoveryService
   - CompilationService
   - RuntimeService
   - MarkdownUpdateService
   - LLMService
   - VectorDBService
   - TelemetryService
   - BackfillService
   - GistPublisher

5. **NEW: `docs/diagrams/`:**
   - `pipeline-overview.md` - ASCII diagram of phases
   - `data-flow.md` - Data flow through services
   - `status-state-machine.md` - ExampleStatus transitions

6. **Forward-compatible migration:**
   - Old docs archived to `docs/archive/` (optional)
   - New docs reflect current implementation

### Hard Rules

- ✅ Documentation accuracy: All references match actual code
- ✅ No outdated info: Remove all old architecture references
- ✅ Completeness: Document all services and phases
- ✅ Examples: Include code examples from actual src/

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | All file/module references exist; schema matches database; phases accurate |
| **Completeness** | All services documented; all phases explained; diagrams provided |
| **Clarity** | Easy to understand; logical flow; good examples |
| **Currency** | Matches current implementation; no outdated references |
| **Usability** | Helps developers understand system; enables contribution |

### Now (Runbook)

```bash
# 1. Audit current docs for outdated references
grep -r "validation_orchestrator" docs/
grep -r "patching_service" docs/
grep -r "snippet_versions" docs/

# 2. List actual files in src/
ls -R src/

# 3. Rewrite docs/architecture.md
# Document current orchestrator + services pattern

# 4. Create docs/database-schema.md
# Document current schema from src/core/database.py

# 5. Create docs/phase-flow.md
# Document Phases A-F from orchestrator.py

# 6. Create docs/services.md
# Document all services in src/services/

# 7. Create diagrams
mkdir -p docs/diagrams/
# Create ASCII diagrams

# 8. Review docs against actual code
# Verify all references exist

# 9. Archive old docs (optional)
mkdir -p docs/archive/
mv docs/old-architecture.md docs/archive/ 2>/dev/null || true

# 10. Commit updated docs
git add docs/
git commit -m "docs: align architecture documentation with current implementation"
```

---

## Taskcard IH-04: Repository Hygiene (Pycache Cleanup)

**Status:** Not Started

**Gap Linkage:** Fixes IH-GAP-04 (Empty source packages with __pycache__), IH-GAP-05 (No .gitignore)

**Priority:** 🟢 **LOW** - Hygiene, prevents confusion

**Role:** Senior engineer delivering clean repository structure and proper Git configuration.

### Scope

**Fix:**
- Remove all `__pycache__` directories from src/
- Remove empty packages: src/patching/, src/discovery/, src/api_reference/, src/llm/, src/validation/
- Add comprehensive `.gitignore` for Python projects
- Add `.gitattributes` for consistent line endings
- Clean up any other artifacts (.pyc, .pyo, .DS_Store, etc.)

**Allowed paths:**
- `.gitignore` - NEW: comprehensive ignore rules
- `.gitattributes` - NEW: line ending rules
- `src/` - remove empty packages and __pycache__
- `CONTRIBUTING.md` - NEW: contribution guidelines with hygiene rules

**Forbidden:** Any other file/path (don't delete actual source files)

### Acceptance Checks

**CLI:**
- Run `find . -name "__pycache__" -type d` - no results
- Run `find . -name "*.pyc" -o -name "*.pyo"` - no results
- Verify empty packages removed
- Verify .gitignore prevents future pycache

**UI/Web/API:**
- N/A (repository hygiene)

**Tests:**
- No tests required (hygiene task)
- Verify imports still work after cleanup

**Config respected end-to-end:**
- N/A (repository hygiene)

**No mock data in production paths:**
- N/A (repository hygiene)

### Deliverables

1. **NEW: `.gitignore`:**
   ```gitignore
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .Python
   build/
   develop-eggs/
   dist/
   downloads/
   eggs/
   .eggs/
   lib/
   lib64/
   parts/
   sdist/
   var/
   wheels/
   share/python-wheels/
   *.egg-info/
   .installed.cfg
   *.egg
   MANIFEST

   # Virtual environments
   venv/
   ENV/
   env/
   .venv

   # IDEs
   .vscode/
   .idea/
   *.swp
   *.swo
   *~
   .DS_Store

   # Testing
   .pytest_cache/
   .coverage
   htmlcov/
   .tox/

   # Database
   *.db
   *.db-journal
   data/*.db
   data/*.db-wal
   data/*.db-shm

   # Artifacts
   artifacts/
   workspace/
   local-telemetry/
   cache/

   # ChromaDB
   data/chroma/

   # Logs
   *.log
   logs/

   # Temporary files
   *.tmp
   *.temp
   .~lock.*
   ```

2. **NEW: `.gitattributes`:**
   ```gitattributes
   # Auto detect text files and normalize line endings to LF
   * text=auto

   # Python files
   *.py text eol=lf

   # Shell scripts
   *.sh text eol=lf

   # JSON, YAML, XML
   *.json text eol=lf
   *.yaml text eol=lf
   *.yml text eol=lf
   *.xml text eol=lf

   # Markdown
   *.md text eol=lf

   # Binary files
   *.db binary
   *.sqlite binary
   *.zip binary
   *.7z binary
   *.rar binary
   *.gz binary
   *.tar binary
   *.png binary
   *.jpg binary
   *.jpeg binary
   *.gif binary
   ```

3. **Cleanup Script: `scripts/clean-repo.sh`:**
   ```bash
   #!/bin/bash
   # Repository hygiene cleanup script

   echo "Cleaning Python cache files..."
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
   find . -type f -name "*.pyc" -delete
   find . -type f -name "*.pyo" -delete
   find . -type f -name "*.py[cod]" -delete

   echo "Cleaning empty packages..."
   # Only remove if empty (no .py files)
   for dir in src/patching src/discovery src/api_reference src/llm src/validation; do
       if [ -d "$dir" ]; then
           if [ -z "$(find $dir -name '*.py' -not -name '__init__.py')" ]; then
               echo "  Removing empty package: $dir"
               rm -rf "$dir"
           fi
       fi
   done

   echo "Cleaning OS artifacts..."
   find . -type f -name ".DS_Store" -delete
   find . -type f -name "Thumbs.db" -delete
   find . -type f -name ".~lock.*" -delete

   echo "Cleaning editor artifacts..."
   find . -type f -name "*.swp" -delete
   find . -type f -name "*.swo" -delete
   find . -type f -name "*~" -delete

   echo "Repository cleanup complete!"
   ```

4. **NEW: `CONTRIBUTING.md`:**
   ```markdown
   # Contributing to Example Reviewer

   ## Development Setup

   1. Clone the repository
   2. Create virtual environment: `python -m venv venv`
   3. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
   4. Install dependencies: `pip install -r requirements.txt`
   5. Install dev dependencies: `pip install -r requirements-dev.txt`

   ## Repository Hygiene

   Before committing:

   1. **Remove cache files**: `./scripts/clean-repo.sh`
   2. **Format code**: `black src/ tests/`
   3. **Lint**: `pylint src/`
   4. **Run tests**: `pytest tests/`

   ## Git Workflow

   1. Create feature branch: `git checkout -b feature/your-feature`
   2. Make changes
   3. Clean repository: `./scripts/clean-repo.sh`
   4. Commit: `git commit -m "feat: your feature"`
   5. Push: `git push origin feature/your-feature`
   6. Create Pull Request

   ## Code Style

   - Follow PEP 8
   - Use type hints
   - Write docstrings for public functions
   - Keep functions small and focused

   ## Testing

   - Write tests for new features
   - Maintain >80% code coverage
   - Run tests before committing: `pytest tests/`

   ## Don't Commit

   - `__pycache__/` directories
   - `.pyc` files
   - Personal IDE configurations
   - Database files (*.db)
   - Artifacts and logs
   - Virtual environments

   These are covered by `.gitignore`.
   ```

5. **Cleanup actions:**
   ```bash
   # Remove __pycache__
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

   # Remove empty packages
   rm -rf src/patching/__pycache__
   rm -rf src/discovery/__pycache__
   rm -rf src/api_reference/__pycache__
   rm -rf src/llm/__pycache__
   rm -rf src/validation/__pycache__

   # Remove packages if they're truly empty (no .py files)
   # Check each package first!
   ```

6. **Forward-compatible migration:**
   - .gitignore prevents future __pycache__
   - Clean repository structure
   - No breaking changes to imports

### Hard Rules

- ✅ Don't delete source files: Only remove cache and empty packages
- ✅ Verify imports: Ensure no broken imports after cleanup
- ✅ Comprehensive .gitignore: Cover all common Python artifacts
- ✅ Document hygiene: CONTRIBUTING.md explains rules

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Only artifacts removed; no source files deleted; imports work |
| **Completeness** | All cache removed; .gitignore comprehensive; .gitattributes added |
| **Safety** | No breaking changes; verified before/after imports work |
| **Documentation** | CONTRIBUTING.md explains hygiene; cleanup script documented |
| **Prevention** | .gitignore prevents future pollution; guidelines clear |

### Now (Runbook)

```bash
# 1. Backup repository (safety)
git status
git stash  # if needed

# 2. Verify what will be removed
find . -name "__pycache__" -type d
find . -name "*.pyc" -o -name "*.pyo"

# 3. List empty packages
for dir in src/patching src/discovery src/api_reference src/llm src/validation; do
    echo "=== $dir ==="
    ls -la $dir 2>/dev/null || echo "Does not exist"
    find $dir -name "*.py" 2>/dev/null || echo "No .py files"
done

# 4. Create .gitignore
# Copy content from deliverable #1

# 5. Create .gitattributes
# Copy content from deliverable #2

# 6. Create scripts/clean-repo.sh
mkdir -p scripts
# Copy content from deliverable #3
chmod +x scripts/clean-repo.sh

# 7. Run cleanup script
./scripts/clean-repo.sh

# 8. Verify imports still work
python -c "import src.pipeline.orchestrator; print('OK')"
python -c "import src.services.discovery_service; print('OK')"

# 9. Create CONTRIBUTING.md
# Copy content from deliverable #4

# 10. Test pipeline still works
python -m cli scan --family zip --max-files 1

# 11. Stage and commit
git add .gitignore .gitattributes scripts/ CONTRIBUTING.md
git add -u  # Stage deletions
git commit -m "chore: repository hygiene - remove pycache, add .gitignore"

# 12. Verify clean working tree
git status
# Should show: nothing to commit, working tree clean
```

---

## Summary

**4 Taskcards Created to Address Infrastructure Gaps (3 Active, 1 Not Needed):**

| Priority | Taskcard | Impact | Effort | Status |
|----------|----------|--------|--------|--------|
| ~~🔥 CRITICAL~~ | ~~**IH-01**: Add Config Scaffolding~~ | ~~Unblocks all pipeline usage~~ | ~~4h~~ | ✅ **NOT NEEDED** |
| 🔥 HIGH | **IH-02**: Fix CLI Entry Point | User-facing contract alignment | 3h | ⚠️ Important |
| 🟡 MEDIUM | **IH-03**: Align Architecture Docs | Removes developer confusion | 8h | ⚠️ Quality |
| 🟢 LOW | **IH-04**: Repository Hygiene | Clean structure, prevent pollution | 2h | ⚠️ Hygiene |

**Implementation Order:**
```
[NOT NEEDED] ✅ IH-01: Config Scaffolding  ← Configs already exist in repository
[HIGH]       ⚠️ IH-02: CLI Entry Point     ← User-facing contract (START HERE)
[MEDIUM]     ⚠️ IH-03: Documentation       ← Developer experience
[LOW]        ⚠️ IH-04: Repository Hygiene  ← Nice-to-have cleanup
```

**Key Deliverables (Excluding IH-01):**
- ~~`config/families/zip.json`~~ - **Already exists**
- ~~`config/global.json`~~ - **Already exists**
- ~~`config/README.md`~~ - Optional enhancement (not critical)
- `cli/__main__.py` - Top-level entry point
- `setup.py` - Proper package setup
- `.gitignore` - Comprehensive ignore rules
- Updated `docs/` - Accurate architecture docs
- `CONTRIBUTING.md` - Hygiene guidelines

**Expected Outcomes:**
- ~~**Immediate usability**: Pipeline runs out-of-the-box~~ - **Already works with existing configs**
- **Consistent CLI**: Documented command works as written
- **Accurate docs**: No misleading references
- **Clean repository**: No __pycache__ pollution

**Total Estimated Effort:** 13 hours (~1.5 days for active taskcards, down from 17h)

**Risk Assessment:**
- **Low Risk**: All active taskcards are additive or cleanup (no breaking changes)
- **High Value**: Removes confusion and improves developer experience
- **Quick Win**: IH-04 can be done in 2 hours for immediate cleanup
