Key Design Decisions
Architecture:

Stage 4.5 (optional) - Runs after compilation success, before finalization
Opt-in via tagging - Only validates snippets marked with runtime_validation_enabled = 1
Medium security - Subprocess isolation with timeouts, no Docker/VMs needed
Components:

RuntimeExecutionManager - Executes code safely in isolated subprocess
TestDataManager - Organizes sample files (PDFs, ZIPs, etc.) per family
ExecutionResultAnalyzer - Parses exceptions from output (NullReferenceException, StreamClosedException, etc.)
RuntimeTaggingService - Auto-tags snippets based on code patterns
Database Changes:

Add runtime_validation_enabled and runtime_test_params columns to snippets table
New execution_results table for storing runtime execution outcomes
New view v_runtime_failures for reporting
Workflow:

Tag snippets for runtime validation (manual SQL, CLI command, or auto-tag via patterns)
Run validation with --runtime flag
After compilation succeeds, Stage 4.5 executes the code with test data
Captures stdout/stderr/exceptions and stores in database
Optionally downgrades to 'needs-fix' if strict_mode enabled
The plan maintains consistency with your existing patterns (WorkspaceManager, ValidationOrchestrator) and provides clear implementation steps with all critical files identified.

Claude’s Plan
Runtime Validation System Implementation Plan
Overview
Add runtime validation capabilities to detect exceptions, resource errors, and API failures through safe execution of compiled C# snippets. This extends the existing 5-stage validation pipeline with an optional Stage 4.5 that runs after compilation success.

Scope: Curated/tagged snippets only (opt-in, not automatic for all snippets)

Safety: Medium security - separate process with timeouts and working directory isolation

Test Data: Sample files (PDFs, ZIPs, documents) organized per family

Architecture Summary
New Stage: 4.5 - Runtime Validation (Optional)
Inserted after Stage 4 (Persistent Ollama auto-fix), triggered only for snippets tagged with runtime_validation_enabled = 1:

Check if snippet is tagged for runtime validation
Load test parameters from database + family config
Execute compiled code in isolated subprocess with timeout
Capture stdout, stderr, exit code, and exceptions
Analyze output for runtime errors (NullReferenceException, stream closed, API errors)
Store results in new execution_results table
Optionally downgrade status to 'needs-fix' if strict mode enabled
Component Overview

RuntimeExecutionManager     → Executes code safely in subprocess
├─ TestDataManager         → Manages sample files per family
├─ ExecutionResultAnalyzer → Parses exceptions and errors from output
└─ RuntimeTaggingService   → Auto-tags snippets based on patterns
Database Changes
1. Add columns to snippets table

ALTER TABLE snippets ADD COLUMN runtime_validation_enabled BOOLEAN DEFAULT 0;
ALTER TABLE snippets ADD COLUMN runtime_test_params TEXT;  -- JSON

CREATE INDEX IF NOT EXISTS idx_snippets_runtime_enabled
ON snippets(runtime_validation_enabled);
Purpose: Tag snippets for runtime validation with test parameters

Example:


{
  "required_files": ["sample.pdf"],
  "expected_behavior": "success",
  "timeout": 30
}
2. New execution_results table

CREATE TABLE IF NOT EXISTS execution_results (
    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snippet_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,
    executed_at TEXT NOT NULL DEFAULT (datetime('now')),

    -- Execution status
    success BOOLEAN NOT NULL,
    timed_out BOOLEAN DEFAULT 0,
    exit_code INTEGER,

    -- Output capture
    stdout TEXT,
    stderr TEXT,

    -- Exception detection
    exception_type TEXT,
    exception_message TEXT,
    stack_trace TEXT,

    -- Performance
    execution_time_ms INTEGER,
    peak_memory_kb INTEGER,

    -- Test data used
    test_params_json TEXT,

    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES snippet_versions(version_id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_execution_results_snippet ON execution_results(snippet_id);
CREATE INDEX IF NOT EXISTS idx_execution_results_success ON execution_results(success);
CREATE INDEX IF NOT EXISTS idx_execution_results_exception ON execution_results(exception_type);
3. Reporting view

CREATE VIEW IF NOT EXISTS v_runtime_failures AS
SELECT
    s.snippet_id,
    s.snippet_ordinal,
    p.relative_path,
    p.family,
    er.exception_type,
    er.exception_message,
    er.executed_at
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
JOIN execution_results er ON s.snippet_id = er.snippet_id
WHERE er.success = 0
ORDER BY er.executed_at DESC;
Family Configuration Extension
Add runtime_validation section to family configs (e.g., config/families/pdf.json):


{
  "family": "pdf",
  "runtime_validation": {
    "enabled": true,
    "mode": "tagged_only",
    "strict_mode": false,
    "timeout": 30,
    "max_memory_mb": 512,

    "auto_tag_patterns": [
      {
        "description": "Document constructor patterns",
        "code_pattern": "new Document\\(",
        "test_params": {
          "required_files": ["sample.pdf"],
          "expected_behavior": "success"
        }
      },
      {
        "description": "Text extraction patterns",
        "code_pattern": "TextAbsorber",
        "test_params": {
          "required_files": ["sample.pdf"],
          "expected_behavior": "produces_output"
        }
      }
    ],

    "default_test_params": {
      "required_files": ["sample.pdf"],
      "expected_behavior": "success",
      "timeout": 30
    }
  }
}
Configuration fields:

enabled: Master switch for runtime validation
mode: "tagged_only" (only validate tagged snippets) or "all_verified" (all compiled snippets)
strict_mode: If true, downgrade status to 'needs-fix' on runtime failure; if false, mark as 'verified-with-warnings'
timeout: Execution timeout in seconds
auto_tag_patterns: Regex patterns to automatically tag snippets during discovery
default_test_params: Default test parameters for tagged snippets
Test Data Organization
Directory Structure

example-reviewer/
└── test-data/
    ├── pdf/
    │   ├── manifest.json
    │   ├── sample.pdf
    │   └── encrypted.pdf
    ├── zip/
    │   ├── manifest.json
    │   └── sample.zip
    ├── words/
    │   ├── manifest.json
    │   └── sample.docx
    ├── cells/
    │   ├── manifest.json
    │   └── sample.xlsx
    └── shared/
        └── common files
Manifest Format (test-data/pdf/manifest.json)

{
  "family": "pdf",
  "test_files": {
    "sample.pdf": {
      "description": "Simple single-page PDF for basic operations",
      "size_bytes": 15234,
      "tags": ["basic", "single-page"]
    },
    "encrypted.pdf": {
      "description": "Password-protected PDF (password: 'test123')",
      "tags": ["security", "encryption"],
      "metadata": {
        "password": "test123"
      }
    }
  }
}
Purpose:

Documents available test files per family
Provides metadata for special files (passwords, expected behavior)
Centralizes test data management
Implementation Components
1. RuntimeExecutionManager
File: src/validation/execution/runtime_executor.py

Responsibilities:

Execute compiled C# code in isolated subprocess
Apply timeout enforcement (default 30s)
Capture stdout, stderr, exit code
Isolate working directory per execution
Cleanup after execution
Key Methods:


def execute_snippet(snippet_id, code, test_params) -> ExecutionResult
    1. Create isolated execution workspace
    2. Stage test data files (via TestDataManager)
    3. Build executable from compiled code
    4. Run in subprocess with timeout and cwd isolation
    5. Parse output for exceptions/errors
    6. Cleanup workspace
    7. Return ExecutionResult
Safety Implementation:

Each execution runs in separate subprocess (subprocess.run)
Timeout enforced via timeout parameter (default 30s)
Working directory isolated to workspaces/<family>/execution/run_<uuid>/
Restricted environment variables (no sensitive data)
Automatic cleanup of execution workspace after run
Pattern: Extends WorkspaceManager pattern but focuses on execution vs compilation

2. TestDataManager
File: src/validation/execution/test_data_manager.py

Responsibilities:

Load manifests from test-data/<family>/manifest.json
Resolve test file paths
Copy test files to execution workspace
Substitute file paths in test parameters
Key Methods:


def get_test_file(family, file_key) -> Path
def stage_test_data(snippet_id, family, test_params, target_dir) -> Dict
    → Copies required_files to target_dir/input/
    → Creates target_dir/output/ for results
    → Returns paths dict for substitution
3. ExecutionResultAnalyzer
File: src/validation/execution/execution_analyzer.py

Responsibilities:

Parse stdout/stderr for exceptions
Detect common runtime errors (NullReferenceException, StreamClosedException, FileNotFoundException)
Extract stack traces
Identify resource errors beyond exceptions
Exception Patterns:


EXCEPTION_PATTERNS = {
    'NullReferenceException': r'System\.NullReferenceException',
    'ArgumentException': r'System\.ArgumentException',
    'FileNotFoundException': r'System\.IO\.FileNotFoundException',
    'StreamClosedException': r'ObjectDisposedException.*Stream',
    'OutOfMemoryException': r'System\.OutOfMemoryException'
}
Detection Logic:

Parse combined stdout+stderr with regex
Extract exception type, message, stack trace
Detect resource errors (stream closed, file not found, API errors)
Return structured ExecutionAnalysis object
4. RuntimeTaggingService (Optional Enhancement)
File: src/validation/execution/runtime_tagging.py

Responsibilities:

Auto-tag snippets based on code patterns
Apply default test parameters from family config
Update database with tagging metadata
When to tag:

During discovery (after snippet extraction)
During validation (after compilation success)
Manually via SQL or CLI command
Integration with ValidationOrchestrator
Modified validate_snippet() method
File: src/validation/orchestrator.py

Changes:

After Stage 4 success (line ~320-328), add Stage 4.5:


# Stage 4.5: Optional Runtime Validation
if result['status'] == 'verified':
    snippet = self.db.get_snippet(snippet_id)
    if self._should_run_runtime_validation(snippet):
        result['stages_completed'].append('runtime_validation')

        runtime_result = self._execute_runtime_validation(
            snippet_id,
            result['final_code'],
            run_id
        )

        if not runtime_result.success:
            result['runtime_errors'] = runtime_result.errors

            # Strict mode: downgrade to needs-fix
            if self.family_config.get('runtime_validation', {}).get('strict_mode', False):
                result['status'] = 'needs-fix'
                result['message'] = f'Runtime validation failed: {runtime_result.summary}'
                self.db.update_snippet(snippet_id, status='needs-fix')
            # Lenient mode: keep verified with warnings
            else:
                result['runtime_warnings'] = runtime_result.errors
                result['message'] += f' (Runtime warnings: {runtime_result.summary})'
Helper Methods to Add:


def _should_run_runtime_validation(self, snippet: Snippet) -> bool:
    """Check if snippet should undergo runtime validation."""
    runtime_config = self.family_config.get('runtime_validation', {})

    if not runtime_config.get('enabled', False):
        return False

    if runtime_config.get('mode') == 'tagged_only':
        return bool(snippet.runtime_validation_enabled)

    return False

def _execute_runtime_validation(self, snippet_id: int, code: str, run_id: int) -> RuntimeResult:
    """Execute runtime validation for a snippet."""
    snippet = self.db.get_snippet(snippet_id)
    test_params = json.loads(snippet.runtime_test_params or '{}')

    # Merge with defaults
    default_params = self.family_config.get('runtime_validation', {}).get('default_test_params', {})
    test_params = {**default_params, **test_params}

    # Execute with RuntimeExecutionManager
    runtime_executor = RuntimeExecutionManager(
        self.workspace,
        self.family_config,
        self.test_data_manager
    )

    execution_result = runtime_executor.execute_snippet(snippet_id, code, test_params)

    # Store in database
    self.db.create_execution_result(
        snippet_id=snippet_id,
        version_id=self.db.get_latest_snippet_version(snippet_id, 'current').version_id,
        run_id=run_id,
        success=execution_result.success,
        timed_out=execution_result.timed_out,
        exit_code=execution_result.exit_code,
        stdout=execution_result.stdout,
        stderr=execution_result.stderr,
        exception_type=execution_result.exception_type,
        exception_message=execution_result.exception_message,
        execution_time_ms=execution_result.execution_time_ms,
        test_params_json=json.dumps(test_params)
    )

    return execution_result
CLI Commands
1. Existing validate command enhancement
File: src/cli.py

Add --runtime flag:


python -m src.cli validate pdf --runtime
Implementation:


def validate(self, family: str, max_snippets: int = None,
            use_ollama: bool = True, runtime: bool = False):
    """Run validation for a family."""

    # Override family config to enable runtime validation
    if runtime:
        family_config['runtime_validation'] = family_config.get('runtime_validation', {})
        family_config['runtime_validation']['enabled'] = True
        print("[i] Runtime validation enabled for tagged snippets")
2. New verify-runtime command
Purpose: Run ONLY runtime validation on already-compiled snippets (skip compilation)


python -m src.cli verify-runtime pdf
python -m src.cli verify-runtime pdf --snippet-ids 123,456,789
Implementation:


def verify_runtime(self, family: str, snippet_ids: List[int] = None):
    """
    Run ONLY runtime validation on compiled snippets.
    Skips compilation - only executes and tests runtime behavior.
    """
    # 1. Load family config
    # 2. Initialize RuntimeExecutionManager + TestDataManager
    # 3. Get snippets tagged for runtime validation
    # 4. For each snippet:
    #    - Get current verified code
    #    - Load test params
    #    - Execute and store results
    # 5. Print summary statistics
3. New tag-runtime command (Manual Tagging)
Purpose: Manually tag snippets for runtime validation


python -m src.cli tag-runtime pdf 123 --files sample.pdf --behavior success
python -m src.cli tag-runtime pdf --auto-tag  # Use patterns from config
Tagging Workflow
Option 1: Manual SQL Tagging

UPDATE snippets
SET runtime_validation_enabled = 1,
    runtime_test_params = '{"required_files": ["sample.pdf"], "expected_behavior": "success"}'
WHERE snippet_id = 123;
Option 2: CLI Tagging (via new command)

python -m src.cli tag-runtime pdf 123 --files sample.pdf --behavior success
Option 3: Auto-Tagging (During Discovery)
Trigger: During snippet discovery or validation

Logic:


class RuntimeTaggingService:
    def auto_tag_snippet(self, snippet_id: int, code: str, family_config: Dict):
        runtime_config = family_config.get('runtime_validation', {})

        if not runtime_config.get('enabled'):
            return

        # Check auto-tag patterns
        for pattern in runtime_config.get('auto_tag_patterns', []):
            if re.search(pattern['code_pattern'], code):
                test_params = pattern.get('test_params', {})
                self.db.execute(
                    """UPDATE snippets
                       SET runtime_validation_enabled = 1,
                           runtime_test_params = ?
                       WHERE snippet_id = ?""",
                    (json.dumps(test_params), snippet_id)
                )
                break
Telemetry Integration
File: src/core/telemetry.py

Add context manager for runtime execution tracking:


@contextmanager
def track_runtime_execution(self, snippet_id: int):
    """Track runtime execution metrics."""
    start_time = time.time()

    self.log_event("runtime_execution_started", "debug",
                  f"Executing snippet {snippet_id}")

    try:
        yield
        duration_ms = int((time.time() - start_time) * 1000)

        self.log_event("runtime_execution_completed", "info",
                      f"Runtime execution completed for snippet {snippet_id}",
                      {"snippet_id": snippet_id, "duration_ms": duration_ms})

        self.increment_metric('runtime_executions_completed')

    except subprocess.TimeoutExpired:
        self.log_event("runtime_execution_timeout", "warning",
                      f"Runtime execution timed out for snippet {snippet_id}")
        self.increment_metric('runtime_execution_timeouts')
        raise

    except Exception as e:
        self.log_event("runtime_execution_failed", "error",
                      f"Runtime execution failed: {e}")
        self.increment_metric('runtime_execution_failures')
        raise
Critical Files to Modify/Create
Create New:
src/validation/execution/__init__.py - Package init
src/validation/execution/runtime_executor.py - RuntimeExecutionManager
src/validation/execution/test_data_manager.py - TestDataManager
src/validation/execution/execution_analyzer.py - ExecutionResultAnalyzer
src/validation/execution/runtime_tagging.py - RuntimeTaggingService (optional)
Modify Existing:
src/validation/orchestrator.py - Add Stage 4.5 integration (around line 320)
src/cli.py - Add --runtime flag and verify-runtime command
schema.sql - Add columns and table via migration
src/core/telemetry.py - Add runtime tracking context manager
src/core/database.py - Add methods for execution_results table
Configure:
config/families/pdf.json - Add runtime_validation section
config/families/zip.json - Add runtime_validation section
(Repeat for all families: words, cells, email, imaging, slides)
Test Data:
Create test-data/ directory structure
Add sample files per family (pdf, zip, words, cells, etc.)
Create manifest.json for each family
Verification Plan
Phase 1: Manual Testing (Single Snippet)
Tag a simple PDF snippet for runtime validation:


UPDATE snippets SET runtime_validation_enabled = 1,
    runtime_test_params = '{"required_files": ["sample.pdf"], "expected_behavior": "success"}'
WHERE snippet_id = <test-snippet-id>;
Run validation with runtime enabled:


python -m src.cli validate pdf --runtime --max-snippets 1
Verify execution result in database:


SELECT * FROM execution_results WHERE snippet_id = <test-snippet-id>;
Check output: Confirm stdout/stderr captured, exception_type detected (if any)

Phase 2: Batch Testing (Family)
Auto-tag snippets using patterns from config
Run validation on tagged snippets:

python -m src.cli validate pdf --runtime
Review failures:

SELECT * FROM v_runtime_failures WHERE family = 'pdf';
Phase 3: Standalone Runtime Verification
Run verify-runtime command (skip compilation):

python -m src.cli verify-runtime pdf
Compare results with Stage 4 compilation results
Validate performance: Check execution times are within timeout limits
Phase 4: Multi-Family Verification
Test all families with runtime validation enabled
Check resource usage: Confirm medium security (no resource leaks)
Verify cleanup: Confirm execution workspaces are cleaned up
Success Criteria
✅ Runtime validation runs after compilation success (Stage 4.5)
✅ Snippets can be tagged for runtime validation (manual + auto)
✅ Execution happens in isolated subprocess with timeout
✅ Exceptions and errors are captured and stored in database
✅ Test data is organized per family and staged correctly
✅ CLI commands work: validate --runtime and verify-runtime
✅ No runtime validation for untagged snippets (opt-in only)
✅ Strict mode downgrades status to 'needs-fix' on failure
✅ Telemetry tracks runtime execution metrics
✅ Execution workspaces are cleaned up after runs

Future Enhancements (Out of Scope)
Docker/container-based execution for high security
Expected output validation (not just success/failure)
Performance profiling (memory usage, CPU time)
Automated test case generation from API documentation
Cross-family test data sharing
Retry logic for transient failures
Integration with CI/CD for continuous runtime validation
