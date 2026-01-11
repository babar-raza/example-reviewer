# Aspose Example Review System - Implementation Plan

**Project:** Generic Example Review and Validation System
**Pilot Family:** Aspose.ZIP
**Date:** 2026-01-09
**Status:** Plan Ready for Approval

---

## Executive Summary

This plan defines a **generic, database-driven system** for reviewing, validating, and fixing code examples across all Aspose product families. The system will:

- **Discover** code snippets from markdown content across 5 sites (blog, docs, kb, reference, products)
- **Validate** snippets by compiling against latest NuGet packages
- **Fix** issues using pattern-based rules + local Ollama LLM
- **Patch** content files with verified code
- **Track** all operations in SQLite database with full provenance
- **Integrate** with local-telemetry for observability

**Pilot Scope:** Process all 1,401+ Aspose.ZIP examples across 172 pages (37 language translations).

---

## IMPORTANT: English Pages Only

**CRITICAL REQUIREMENT:** The system processes **ONLY English pages** for validation and fixing.

**Rationale:**
1. **Translation Consistency:** Non-English pages are translations of English content and may have translation artifacts or inconsistencies that cause false failures
2. **Code Uniformity:** C# code snippets should be identical across all language versions (only prose text differs)
3. **Efficient Workflow:** Validate and fix English pages first, then replicate fixes to all translations
4. **Reduced False Positives:** Avoids validation failures due to translation issues rather than code problems

**Implementation:**
- Discovery service detects page language from filename pattern:
  - `index.md` → English (process)
  - `index.de.md` → German (skip)
  - `index.ar.md` → Arabic (skip)
  - etc.
- Only English pages are stored in database during discovery
- Translation update strategy handled in separate deployment phase

**Expected Impact:**
- **Before:** 77,386 snippets discovered (all 37 languages)
- **After:** ~2,092 snippets discovered (English only, 77386/37)
- **Quality:** Higher validation success rate due to consistent English content

---

## Architecture Overview

### High-Level Pipeline

```
┌──────────────┐
│  Discovery   │  Scan markdown files → Extract snippets → Store in DB
└──────┬───────┘
       │
┌──────▼───────┐
│ Validation   │  Compile snippets → Apply fixes → Retry with Ollama
└──────┬───────┘
       │
┌──────▼───────┐
│   Patching   │  Generate diffs → Safety checks → LLM verify format
└──────┬───────┘
       │
┌──────▼───────┐
│ Deployment   │  Apply patches → Update translations → Commit
└──────────────┘
```

### Components

1. **Discovery Service** (`src/discovery_service.py`)
   - Scans content directories for markdown files
   - **Filters to English pages only** (skips translations like .de.md, .ar.md, etc.)
   - Extracts C# code fences only (skips non-code content)
   - Generates stable snippet locators (not line-number dependent)
   - Stores pages + snippets in database

2. **Validation Orchestrator** (`src/validation_orchestrator.py`)
   - 5-stage validation pipeline (see below)
   - Downloads NuGet packages per family config
   - Compiles snippets using Roslyn
   - Applies pattern fixes + Ollama auto-fix
   - Records all attempts in database

3. **Pattern Registry** (`src/pattern_registry.py`)
   - Loads detection/fix patterns from family configs
   - Pluggable pattern handlers
   - Tracks which fixes were applied

4. **Ollama Integration** (`src/ollama_integration.py`)
   - Model selection (prefers code models: qwen2.5-coder, deepseek-coder)
   - Prompt engineering for code fixing
   - Response parsing with safety limits

5. **Snippet Locator** (`src/snippet_locator.py`)
   - Stable identifiers using heading context + content hash
   - Resilient to line number changes
   - Enables precise snippet replacement

6. **Patch Generator** (`src/patch_generator.py`)
   - Generates unified diffs for verified snippets
   - Safety validation (no frontmatter changes, size limits)
   - Creates `.patch` files with metadata

7. **Content Patcher** (`src/content_patcher.py`)
   - Applies patches to markdown files
   - Preserves formatting and structure
   - Only overwrites existing snippets (no new pages)

8. **LLM Page Verifier** (`src/llm_page_verifier.py`)
   - Full-page formatting check using Ollama
   - Detects formatting issues introduced by patching
   - Only fixes system-introduced issues

9. **Telemetry Client** (`src/telemetry.py`)
   - Dual-write to NDJSON + SQLite
   - Context managers for tracking operations
   - Integration with local-telemetry HTTP API

10. **CLI Interface** (`src/cli.py`)
    - Command-line interface for all operations
    - Progress reporting and logging

---

## Data Model

### SQLite Schema (`scripts/example-reviewer/data/examples.db`)

**Table: `pages`**
```sql
CREATE TABLE pages (
    page_id INTEGER PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    site TEXT NOT NULL,  -- blog | docs | kb | reference | products
    family TEXT NOT NULL,
    language TEXT NOT NULL,  -- en, de, es, etc.
    state TEXT NOT NULL,  -- unscanned | scanned | validated | patched | deployed
    content_hash TEXT,
    last_scanned_at TEXT,
    last_validated_at TEXT,
    last_patched_at TEXT,
    snippet_count INTEGER DEFAULT 0,
    verified_snippet_count INTEGER DEFAULT 0
);
```

**Table: `snippets`**
```sql
CREATE TABLE snippets (
    snippet_id INTEGER PRIMARY KEY,
    page_id INTEGER NOT NULL,
    snippet_ordinal INTEGER NOT NULL,  -- 1-indexed position on page
    locator_json TEXT NOT NULL,  -- SnippetLocator serialized
    snippet_type TEXT NOT NULL,  -- fence | gist
    language TEXT,  -- csharp, vb, etc.
    status TEXT NOT NULL,  -- unverified | verified | needs-fix | skipped
    first_seen_at TEXT NOT NULL,
    last_validated_at TEXT,
    validation_attempts INTEGER DEFAULT 0,
    FOREIGN KEY (page_id) REFERENCES pages(page_id),
    UNIQUE(page_id, snippet_ordinal)
);
```

**Table: `snippet_versions`**
```sql
CREATE TABLE snippet_versions (
    version_id INTEGER PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    version_type TEXT NOT NULL,  -- original | fixed | current | before_fix
    code_content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT,  -- system | pattern | ollama | manual
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id)
);
```

**Table: `runs`**
```sql
CREATE TABLE runs (
    run_id INTEGER PRIMARY KEY,
    run_type TEXT NOT NULL,  -- discovery | validation | patching | verification
    family TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,  -- running | completed | failed | cancelled
    pages_processed INTEGER DEFAULT 0,
    snippets_processed INTEGER DEFAULT 0,
    config_snapshot TEXT  -- JSON snapshot of family config
);
```

**Table: `run_events`**
```sql
CREATE TABLE run_events (
    event_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,  -- debug | info | warning | error
    message TEXT NOT NULL,
    details_json TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

**Table: `snippet_issues`**
```sql
CREATE TABLE snippet_issues (
    issue_id INTEGER PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL,  -- pattern name or error category
    description TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id)
);
```

**Table: `fixes_applied`**
```sql
CREATE TABLE fixes_applied (
    fix_id INTEGER PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    issue_id INTEGER,
    fix_type TEXT NOT NULL,  -- pattern | ollama | manual
    description TEXT NOT NULL,
    before_version_id INTEGER,
    after_version_id INTEGER,
    applied_at TEXT NOT NULL,
    successful BOOLEAN NOT NULL,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id),
    FOREIGN KEY (issue_id) REFERENCES snippet_issues(issue_id),
    FOREIGN KEY (before_version_id) REFERENCES snippet_versions(version_id),
    FOREIGN KEY (after_version_id) REFERENCES snippet_versions(version_id)
);
```

**Table: `build_attempts`**
```sql
CREATE TABLE build_attempts (
    attempt_id INTEGER PRIMARY KEY,
    snippet_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    run_id INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    compiler_output TEXT,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    attempted_at TEXT NOT NULL,
    FOREIGN KEY (snippet_id) REFERENCES snippets(snippet_id),
    FOREIGN KEY (version_id) REFERENCES snippet_versions(version_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

**Views for Reporting:**
```sql
CREATE VIEW v_active_snippets AS
SELECT s.*, p.file_path, p.relative_path, p.family, p.language
FROM snippets s
JOIN pages p ON s.page_id = p.page_id
WHERE s.status != 'skipped';

CREATE VIEW v_run_statistics AS
SELECT
    r.run_id, r.run_type, r.family, r.status,
    r.pages_processed, r.snippets_processed,
    COUNT(CASE WHEN re.severity = 'error' THEN 1 END) as error_count,
    COUNT(CASE WHEN re.severity = 'warning' THEN 1 END) as warning_count
FROM runs r
LEFT JOIN run_events re ON r.run_id = re.run_id
GROUP BY r.run_id;

CREATE VIEW v_pages_needing_attention AS
SELECT p.*,
    COUNT(s.snippet_id) as total_snippets,
    COUNT(CASE WHEN s.status = 'needs-fix' THEN 1 END) as needs_fix_count,
    COUNT(CASE WHEN s.status = 'verified' THEN 1 END) as verified_count
FROM pages p
LEFT JOIN snippets s ON p.page_id = s.page_id
WHERE p.state IN ('scanned', 'validated')
GROUP BY p.page_id
HAVING needs_fix_count > 0 OR verified_count < total_snippets;
```

### Artifact Directory Structure

```
scripts/example-reviewer/
├── .venv/                          # Python virtual environment
├── data/
│   ├── examples.db                 # SQLite database (WAL mode)
│   ├── examples.db-wal
│   └── examples.db-shm
├── workspaces/
│   ├── zip/                        # Per-family workspaces
│   │   ├── validator/              # .NET project
│   │   │   ├── Validator.csproj
│   │   │   ├── Program.cs
│   │   │   └── bin/
│   │   ├── snippets/               # Extracted snippets
│   │   │   ├── snippet_123.cs
│   │   │   └── snippet_456.cs
│   │   └── nuget-cache/            # NuGet package cache
│   └── words/
├── artifacts/
│   ├── runs/
│   │   └── run_20260109_143022/
│   │       ├── metadata.json
│   │       ├── events.ndjson       # Dual-write event log
│   │       ├── validation_results.json
│   │       ├── patch_queue.json
│   │       └── report.html
│   ├── patches/
│   │   └── patch_20260109_143530/
│   │       ├── metadata.json
│   │       ├── page_123.patch      # Unified diffs
│   │       └── page_456.patch
│   └── backups/                    # Pre-patch backups
│       └── backup_20260109_143530/
├── logs/
│   ├── discovery.log
│   ├── validation.log
│   └── patching.log
├── reports/
│   ├── page_catalog.json           # Legacy compatibility
│   ├── validation_summary.json
│   └── pilot_report.html
├── config/
│   └── families/
│       ├── zip.json
│       ├── words.json
│       └── pdf.json
├── src/
│   ├── cli.py
│   ├── discovery_service.py
│   ├── validation_orchestrator.py
│   ├── pattern_registry.py
│   ├── ollama_integration.py
│   ├── snippet_locator.py
│   ├── patch_generator.py
│   ├── content_patcher.py
│   ├── llm_page_verifier.py
│   ├── telemetry.py
│   ├── workspace_manager.py
│   └── database.py
├── test-examples/                  # Legacy validator (keep for reference)
├── schema.sql
├── requirements.txt
└── README.md
```

---

## Validation Pipeline (5 Stages)

### Stage 0: Setup
- Create workspace directory for family
- Download NuGet packages from family config
- Initialize .NET validator project with references

### Stage 1: Pattern-Based Pre-Fix
- Load patterns from `config/families/{family}.json`
- Detect issues using regex patterns
- Apply auto-fixes where `auto_apply: true`
- Record all fixes in `fixes_applied` table
- Save fixed version to `snippet_versions`

### Stage 2: Compile Original
- Compile original code (before fixes)
- If successful → mark as `verified`, skip remaining stages
- If failed → record errors, continue to Stage 3

### Stage 3: Compile with Pattern Fixes
- Compile code after pattern fixes
- If successful → mark as `verified`, skip remaining stages
- If failed → record errors, continue to Stage 4

### Stage 4: Ollama Auto-Fix Loop
- **Attempt 1:** Send code + errors to Ollama with fix prompt
  - Parse response, extract fixed code
  - Compile and check result
  - If successful → mark as `verified`, done
  - If failed → continue to Attempt 2

- **Attempt 2:** Send previous attempt + new errors to Ollama
  - Provide context about what didn't work
  - Compile and check result
  - If successful → mark as `verified`, done
  - If failed → continue to Attempt 3

- **Attempt 3:** Final attempt with stricter prompt
  - Emphasize API constraints
  - Compile and check result
  - If successful → mark as `verified`, done
  - If failed → mark as `needs-fix`, flag for manual review

### Stage 5: Finalization
- Save final version to `snippet_versions` (type: `current`)
- Update snippet status in database
- Record validation attempt in `build_attempts`
- Log all events to `run_events`
- Send telemetry to local-telemetry service

### Error Categorization

Compilation errors are categorized for reporting:
- **Missing APIs:** `CS0117` (method not found), `CS1061` (no definition)
- **Type errors:** `CS0246` (type not found), `CS0029` (type conversion)
- **Syntax errors:** `CS1002` (missing semicolon), etc.
- **Missing references:** `CS0012` (assembly reference required)

---

## Family Configuration Schema

**File:** `config/families/zip.json`

```json
{
  "family": "zip",
  "display_name": "Aspose.ZIP",
  "nuget_config": {
    "primary_package": {
      "name": "Aspose.Zip",
      "version": "*",
      "version_strategy": "latest_stable"
    },
    "additional_packages": [],
    "target_frameworks": ["net8.0"],
    "required_assemblies": [
      "System.Runtime",
      "System.Collections",
      "System.IO.FileSystem",
      "netstandard"
    ]
  },
  "patterns": [
    {
      "name": "deflate_params",
      "description": "DeflateCompressionSettings does NOT accept parameters",
      "detection": {
        "regex": "new\\s+DeflateCompressionSettings\\s*\\([^)]+\\)",
        "flags": ["MULTILINE"]
      },
      "fix": {
        "type": "regex_replace",
        "replacement": "new DeflateCompressionSettings()",
        "auto_apply": true
      },
      "severity": "error"
    },
    {
      "name": "save_async",
      "description": "SaveAsync does NOT exist (hallucination)",
      "detection": {
        "regex": "\\b(await\\s+)?archive\\.SaveAsync\\s*\\(",
        "flags": ["MULTILINE"]
      },
      "fix": {
        "type": "regex_replace",
        "replacement": "archive.Save(",
        "auto_apply": true
      },
      "severity": "error"
    },
    {
      "name": "stream_disposal",
      "description": "Stream disposed before Save() call",
      "detection": {
        "regex": "using\\s*\\([^)]*Stream[^)]*\\)\\s*\\{[^}]*CreateEntry[^}]*\\}[^}]*Save\\s*\\(",
        "flags": ["DOTALL"]
      },
      "fix": {
        "type": "manual",
        "suggestion": "Ensure stream remains valid until after Save() call",
        "auto_apply": false
      },
      "severity": "warning"
    },
    {
      "name": "directory_iteration",
      "description": "Manual iteration instead of CreateEntries",
      "detection": {
        "regex": "Directory\\.GetFiles\\([^)]*\\)[^;]*foreach",
        "flags": ["MULTILINE", "DOTALL"]
      },
      "fix": {
        "type": "suggestion",
        "suggestion": "Consider using archive.CreateEntries(directoryPath, includeRootDirectory)",
        "auto_apply": false
      },
      "severity": "info"
    }
  ],
  "non_existent_apis": [
    "SaveAsync",
    "CreateEntryAsync",
    "CompressAsync",
    "ExtractAsync"
  ],
  "ollama_context": {
    "library_description": "Aspose.ZIP is a .NET library for creating, extracting, and manipulating ZIP archives",
    "common_usings": [
      "using Aspose.Zip;",
      "using Aspose.Zip.Saving;",
      "using System.IO;"
    ]
  }
}
```

---

## Snippet Locator Design

### Stable Identifier (Not Line-Number Dependent)

```python
@dataclass
class SnippetLocator:
    """Stable identifier for a snippet within a markdown file"""

    page_path: str              # Absolute file path
    snippet_ordinal: int        # 1-indexed position (1st snippet, 2nd snippet, etc.)

    # Context for resilience
    heading_context: List[str]  # H1-H6 hierarchy leading to snippet
    preceding_text_hash: str    # Hash of 100 chars before snippet
    snippet_content_hash: str   # SHA256 of original snippet content

    # Advisory only (may change)
    line_start: int             # Starting line number
    line_end: int               # Ending line number
    char_offset_start: int      # Character offset in file
    char_offset_end: int        # Character offset end

    # Metadata
    snippet_type: str           # "fence" | "gist"
    language: str               # "csharp" | "vb" | etc.
    gist_id: Optional[str]      # If type == "gist"
```

### Locator Matching Strategy

When patching, locate snippet using:
1. **Primary:** `page_path + snippet_ordinal + snippet_content_hash`
2. **Fallback 1:** If content changed, use `heading_context + preceding_text_hash`
3. **Fallback 2:** If structure changed, use `char_offset_start` (advisory)

### Storage in Database

Store as JSON in `snippets.locator_json`:
```json
{
  "page_path": "d:\\...\\index.md",
  "snippet_ordinal": 3,
  "heading_context": ["## Working with ZIP Files", "### Create Archive in Memory"],
  "preceding_text_hash": "a3f2b1...",
  "snippet_content_hash": "d9e8c7...",
  "line_start": 89,
  "line_end": 119,
  "char_offset_start": 4523,
  "char_offset_end": 5891,
  "snippet_type": "fence",
  "language": "csharp",
  "gist_id": null
}
```

---

## Ollama Integration

### Model Selection

Auto-detect best available model (in priority order):
1. `qwen2.5-coder:7b` or `qwen2.5-coder:32b`
2. `deepseek-coder:6.7b` or `deepseek-coder:33b`
3. `codellama:7b` or `codellama:13b`
4. `llama3.1:8b` (fallback)

Check with: `ollama list`

### Prompt Template

```python
CODE_FIX_PROMPT_TEMPLATE = """You are a C# code fixer for {family_name} library (NuGet: {nuget_package}).

**YOUR TASK:** Fix ONLY the compilation errors in the code below. Do NOT change the logic or add features.

**COMPILATION ERRORS:**
{error_list}

**IMPORTANT CONSTRAINTS:**
1. The following methods/APIs do NOT EXIST in this library (do not use them):
   {non_existent_apis}

2. Available APIs (use these instead):
   {available_apis}

3. Common imports:
   {common_usings}

**CODE TO FIX:**
```csharp
{code}
```

**INSTRUCTIONS:**
1. Fix ONLY the compilation errors listed above
2. Preserve the original logic and structure
3. Do NOT hallucinate methods from the NON-EXISTENT list
4. Do NOT add try-catch, logging, or error handling unless required for compilation
5. Return ONLY the fixed code inside a single ```csharp code fence

**FIXED CODE:**
"""
```

### Response Parsing

```python
def parse_ollama_response(response: str) -> Optional[str]:
    """Extract code from Ollama response"""

    # Find ```csharp ... ``` fence
    pattern = r'```(?:csharp|c#)\s*\n(.*?)\n```'
    matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

    if not matches:
        return None

    # Take first match
    fixed_code = matches[0].strip()

    # Safety checks
    if len(fixed_code) == 0:
        return None
    if len(fixed_code) > 50000:  # Suspiciously large
        return None

    return fixed_code
```

### Ollama API Call

```python
import requests

def call_ollama(model: str, prompt: str) -> str:
    """Call local Ollama API"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistency
                "top_p": 0.9,
                "max_tokens": 4096
            }
        },
        timeout=120
    )

    response.raise_for_status()
    return response.json()["response"]
```

---

## Patch Generation and Safety

### Unified Diff Format

```diff
--- a/content/blog.aspose.net/zip/example/index.md
+++ b/content/blog.aspose.net/zip/example/index.md
@@ -89,7 +89,7 @@ Here's how to create a ZIP archive:
 ```csharp
 using var archive = new Archive();
-var deflate = new DeflateCompressionSettings(CompressionLevel.Normal);
+var deflate = new DeflateCompressionSettings();
 archive.CreateEntry("file.txt", "data.txt", false, deflate);
 archive.Save("output.zip");
 ```
```

### Patch Metadata

Each `.patch` file includes metadata header:
```yaml
---
patch_id: patch_20260109_143530_page_123
page_path: content/blog.aspose.net/zip/example/index.md
snippet_id: 456
snippet_ordinal: 3
validation_status: verified
build_attempts: 2
fixes_applied:
  - deflate_params (pattern)
  - ollama_attempt_1 (failed)
  - ollama_attempt_2 (success)
created_at: 2026-01-09T14:35:30Z
---
<unified diff content>
```

### Safety Validation Checklist

Before applying patch:
- [ ] Frontmatter unchanged (YAML header must be identical)
- [ ] Only code fence content modified (no prose changes)
- [ ] Diff size < 5000 characters (prevent runaway LLM output)
- [ ] No deletion of headings or structural markdown
- [ ] Snippet locator still matches (content hash or context)
- [ ] No changes to gist shortcode structure (only inline fences)
- [ ] Language attribute preserved (```csharp → ```csharp)
- [ ] Backup created before applying patch

### Post-Patch LLM Verification

After applying patch, verify with Ollama:
```python
LLM_VERIFY_PROMPT = """You are a markdown formatting checker.

**TASK:** Check if this markdown page has correct formatting after automated code snippet updates.

**ORIGINAL PAGE:** (first 1000 chars)
{original_preview}

**UPDATED PAGE:** (full content)
{updated_content}

**CHECK FOR:**
1. Broken markdown syntax (unmatched fences, broken lists, etc.)
2. Formatting issues introduced by patching (extra newlines, indentation)
3. Structural damage (deleted headings, broken links)

**DO NOT CHECK:**
- Code correctness (already validated)
- Content quality or accuracy
- Style or tone

**RESPOND WITH:**
- "OK" if formatting is correct
- List of specific formatting issues if found (be concise)

**YOUR ASSESSMENT:**
"""
```

If issues found → attempt auto-fix → re-verify → if still broken, rollback patch.

---

## Gist Handling Strategy

### Decision Tree

```
Is snippet a gist shortcode?
│
├─ NO → Inline fence
│   └─ Patch normally (replace fence content)
│
└─ YES → Gist reference
    │
    ├─ Is gist file in repo?
    │   └─ YES → Update gist file, keep shortcode
    │
    └─ NO → Check complexity
        │
        ├─ Simple snippet (< 50 lines, no dependencies)?
        │   └─ Replace shortcode with inline fence
        │
        └─ Complex snippet?
            └─ Keep gist, flag for manual update
```

### Gist Shortcode Format

```markdown
{{< gist "aspose-zip" "1234567890abcdef" "example.cs" >}}
```

### Gist File Location (if in repo)

Check: `static/gists/aspose-zip/1234567890abcdef/example.cs`

If exists → update this file instead of inline replacement.

---

## Translation Coordination

### Strategy for 37 Languages

1. **Identify translation groups:**
   - Parse filename patterns: `index.md`, `index.de.md`, `index.es.md`, etc.
   - Group by base path (all translations of same content)

2. **Code snippet comparison:**
   - Extract code from all language versions
   - Compare content hashes

3. **Auto-apply decision:**
   ```python
   if all_translations_have_identical_code(group):
       # Apply same fix to all translations
       apply_patch_to_all(group)
   else:
       # Code differs between languages
       flag_for_manual_review(group)
       # Apply fix only to validated language
   ```

4. **Database tracking:**
   - Each language has separate `page_id` and `snippet_id`
   - Link translations via `translation_group` table (future enhancement)

---

## CLI Interface

### Command Structure

```bash
# Activate venv
cd scripts/example-reviewer
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Discovery phase
python src/cli.py discover --family zip --full-scan

# Validation phase
python src/cli.py validate --family zip --max-pages 10
python src/cli.py validate --family zip --all  # Full validation

# Patching phase (dry-run first)
python src/cli.py patch --family zip --dry-run
python src/cli.py patch --family zip --apply

# Verification phase
python src/cli.py verify --family zip --llm-check

# Reporting
python src/cli.py report --family zip --format html
python src/cli.py report --family zip --format json

# Database inspection
python src/cli.py db-status --family zip
python src/cli.py db-query "SELECT * FROM v_pages_needing_attention"

# Manual fixes
python src/cli.py mark-snippet-verified --snippet-id 123
python src/cli.py skip-snippet --snippet-id 456 --reason "complex-logic"

# Cleanup
python src/cli.py cleanup-workspaces --family zip
python src/cli.py archive-run --run-id 789
```

### Example: Full Pilot Run

```bash
# Step 1: Fresh discovery
python src/cli.py discover --family zip --full-scan
# Output: Found 172 pages, 1401 snippets

# Step 2: Validate (start with sample)
python src/cli.py validate --family zip --max-pages 10
# Output: 10 pages, 42 snippets validated
#         - 28 verified (67%)
#         - 10 needs-fix (24%)
#         - 4 skipped (9%)

# Step 3: Review report
python src/cli.py report --family zip --format html
# Opens: artifacts/runs/run_TIMESTAMP/report.html

# Step 4: Full validation
python src/cli.py validate --family zip --all
# Output: 172 pages, 1401 snippets processed

# Step 5: Generate patches (dry-run)
python src/cli.py patch --family zip --dry-run
# Output: 89 patches generated, 0 applied (dry-run)

# Step 6: Apply patches
python src/cli.py patch --family zip --apply
# Output: 89 patches applied successfully

# Step 7: LLM verification
python src/cli.py verify --family zip --llm-check
# Output: 89 pages verified, 2 formatting issues found and fixed

# Step 8: Final report
python src/cli.py report --family zip --format html --output pilot-report.html
```

---

## Telemetry Integration

### Dual-Write Pattern

```python
class TelemetryClient:
    def __init__(self, telemetry_root: Path, http_url: str):
        self.ndjson_path = telemetry_root / "events.ndjson"
        self.http_url = http_url  # http://localhost:8765/ingest

    def log_event(self, event: Dict[str, Any]):
        # Write 1: NDJSON (crash-resilient)
        with open(self.ndjson_path, 'a') as f:
            f.write(json.dumps(event) + '\n')

        # Write 2: HTTP API (if available)
        try:
            requests.post(self.http_url, json=event, timeout=2)
        except:
            pass  # Non-critical, NDJSON is source of truth
```

### Context Managers

```python
@contextmanager
def track_validation(self, snippet_id: int, family: str):
    """Track validation operation"""
    start = time.time()
    event_data = {
        'event_type': 'validation_started',
        'snippet_id': snippet_id,
        'family': family,
        'timestamp': datetime.utcnow().isoformat()
    }
    self.log_event(event_data)

    try:
        yield
        duration = time.time() - start
        self.log_event({
            'event_type': 'validation_completed',
            'snippet_id': snippet_id,
            'duration_ms': int(duration * 1000),
            'status': 'success'
        })
    except Exception as e:
        self.log_event({
            'event_type': 'validation_failed',
            'snippet_id': snippet_id,
            'error': str(e),
            'status': 'error'
        })
        raise

# Usage
with telemetry.track_validation(snippet_id=123, family='zip'):
    result = validate_snippet(code)
```

---

## Quality Gates

### Stage 1: Discovery
- [ ] All expected content directories scanned
- [ ] Snippet count matches manual spot-check (±10%)
- [ ] No database corruption (integrity check passes)
- [ ] All locators have valid content hashes

### Stage 2: Validation
- [ ] At least 50% of snippets successfully compiled (original or fixed)
- [ ] Pattern fixes applied where expected (based on manual review)
- [ ] Ollama fixes improve compilation rate by >20%
- [ ] No snippet marked as `verified` without successful compilation

### Stage 3: Patching
- [ ] All patches have valid unified diff format
- [ ] No patches modify frontmatter
- [ ] All patches < 5000 characters
- [ ] Backup created for every patched file

### Stage 4: Verification
- [ ] LLM verification detects intentionally broken formatting (test case)
- [ ] No false positives on correctly formatted pages
- [ ] Auto-fix resolves >80% of detected formatting issues

### Stage 5: Pilot Completion
- [ ] Process all 1,401 Aspose.ZIP snippets
- [ ] Generate comprehensive HTML report
- [ ] At least 60% snippets verified (compilable)
- [ ] All changes committed to git with proper messages

---

## Extension Points for Other Families

### Adding a New Family (e.g., Aspose.Words)

1. **Create family config:**
   ```bash
   cp config/families/zip.json config/families/words.json
   ```

   Edit `words.json`:
   - Update `nuget_config.primary_package` → `"Aspose.Words"`
   - Update `patterns` array with family-specific issues
   - Update `non_existent_apis` list
   - Update `ollama_context`

2. **Run discovery:**
   ```bash
   python src/cli.py discover --family words --full-scan
   ```

3. **Run validation:**
   ```bash
   python src/cli.py validate --family words --max-pages 10
   ```

4. **Review and iterate:**
   - Check validation results
   - Add new patterns to `words.json` as needed
   - Update non-existent APIs list

5. **Scale up:**
   ```bash
   python src/cli.py validate --family words --all
   python src/cli.py patch --family words --apply
   ```

### Pattern Handler Plugin

For complex fixes that can't be handled by regex:

```python
# In pattern_registry.py

class PatternHandler(ABC):
    @abstractmethod
    def detect(self, code: str) -> List[PatternMatch]:
        pass

    @abstractmethod
    def apply_fix(self, code: str, match: PatternMatch) -> str:
        pass

# Example: Custom handler for stream disposal
class StreamDisposalHandler(PatternHandler):
    def detect(self, code: str) -> List[PatternMatch]:
        # Complex AST-based analysis
        tree = ast.parse(code)
        # ... find using blocks with streams
        return matches

    def apply_fix(self, code: str, match: PatternMatch) -> str:
        # Transform using block to try-finally
        return fixed_code

# Register in family config:
{
  "patterns": [
    {
      "name": "stream_disposal",
      "handler_class": "StreamDisposalHandler",
      "auto_apply": false
    }
  ]
}
```

---

## Pilot Checklist - Aspose.ZIP

### Pre-Pilot Setup
- [ ] Create venv: `python -m venv scripts/example-reviewer/.venv`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Initialize database: `python src/cli.py init-db`
- [ ] Verify Ollama running: `ollama list`
- [ ] Verify .NET SDK: `dotnet --version` (8.0+)
- [ ] Create `config/families/zip.json` with patterns
- [ ] Verify local-telemetry service: `curl http://localhost:8765/health`

### Phase 1: Discovery
- [ ] Run discovery: `python src/cli.py discover --family zip --full-scan`
- [ ] Verify snippet count: ~1,401 expected
- [ ] Check database: `python src/cli.py db-status --family zip`
- [ ] Spot-check 10 random snippets manually

### Phase 2: Validation (Sample)
- [ ] Run sample validation: `python src/cli.py validate --family zip --max-pages 10`
- [ ] Review report: Check HTML report in `artifacts/runs/`
- [ ] Verify pattern fixes applied correctly
- [ ] Check Ollama fix attempts in database
- [ ] Verify compilation success rate >30%

### Phase 3: Validation (Full)
- [ ] Run full validation: `python src/cli.py validate --family zip --all`
- [ ] Monitor progress (expect ~2-4 hours for 1,401 snippets)
- [ ] Check for errors in logs: `logs/validation.log`
- [ ] Generate interim report: `python src/cli.py report --family zip`
- [ ] Verify compilation success rate >50%

### Phase 4: Patching (Dry-Run)
- [ ] Generate patches: `python src/cli.py patch --family zip --dry-run`
- [ ] Review 5 random patches manually
- [ ] Verify no frontmatter changes
- [ ] Verify no prose text changes
- [ ] Check patch count matches verified snippets

### Phase 5: Patching (Apply)
- [ ] Create git branch: `git checkout -b fix/aspose-zip-examples`
- [ ] Apply patches: `python src/cli.py patch --family zip --apply`
- [ ] Verify backups created in `artifacts/backups/`
- [ ] Spot-check 10 patched files manually

### Phase 6: LLM Verification
- [ ] Run LLM verification: `python src/cli.py verify --family zip --llm-check`
- [ ] Review detected formatting issues
- [ ] Verify auto-fixes applied correctly
- [ ] Manually inspect any unresolved issues

### Phase 7: Reporting
- [ ] Generate final report: `python src/cli.py report --family zip --format html --output pilot-report.html`
- [ ] Review statistics:
  - Total snippets processed
  - Compilation success rate
  - Pattern fixes applied
  - Ollama fixes applied
  - Manual review queue size
- [ ] Document any issues encountered

### Phase 8: Deployment
- [ ] Review git diff: `git diff main`
- [ ] Create commit: `git add -A && git commit -m "Fix Aspose.ZIP examples: validate and patch 1401 snippets"`
- [ ] Push branch: `git push origin fix/aspose-zip-examples`
- [ ] Create pull request with pilot report attached

### Phase 9: Translation Handling
- [ ] Identify translation groups
- [ ] Compare code across translations
- [ ] Apply patches to identical code translations
- [ ] Flag differing translations for manual review

### Post-Pilot Review
- [ ] Calculate time savings (manual vs automated)
- [ ] Identify pattern improvements needed
- [ ] Document any edge cases discovered
- [ ] Plan next family (Aspose.Words? Aspose.PDF?)

---

## Verification Section - How to Test End-to-End

### Test 1: Single Snippet Validation

**Purpose:** Verify the validation pipeline works correctly.

```bash
# Create test snippet
mkdir -p test-snippets
cat > test-snippets/test1.cs << 'EOF'
using Aspose.Zip;
using System.IO;

var archive = new Archive();
var deflate = new DeflateCompressionSettings(CompressionLevel.Normal);  // WRONG
archive.CreateEntry("file.txt", "data.txt", false, deflate);
await archive.SaveAsync("output.zip");  // WRONG
EOF

# Insert into database
python src/cli.py test-insert-snippet --file test-snippets/test1.cs --family zip

# Validate
python src/cli.py validate --snippet-id <ID>

# Expected results:
# - Pattern fix: DeflateCompressionSettings() → no params
# - Pattern fix: SaveAsync → Save
# - Status: verified
# - Build attempts: 3 (original fail, pattern fix success, skip Ollama)
```

### Test 2: Patch Safety Validation

**Purpose:** Verify patches don't break markdown structure.

```bash
# Create test page with intentionally risky structure
cat > test-page.md << 'EOF'
---
title: Test Page
---

## Section 1

```csharp
var x = new DeflateCompressionSettings(param);  // WRONG
```

Some text here.

## Section 2

Content.
EOF

# Process
python src/cli.py discover --file test-page.md --family zip
python src/cli.py validate --file test-page.md
python src/cli.py patch --file test-page.md --apply

# Verify:
# - Frontmatter unchanged (diff --- ... ---)
# - Only code fence modified
# - Headings preserved
# - Prose text unchanged
```

### Test 3: Ollama Integration

**Purpose:** Verify Ollama can fix complex issues.

```bash
# Create snippet with issue requiring LLM
cat > test-snippets/test-ollama.cs << 'EOF'
using Aspose.Zip;

var archive = new Archive();
archive.CreateEntryAsync("file", stream);  // Does not exist
var result = await archive.SaveAsync(ms);  // Does not exist
EOF

# Process with Ollama
python src/cli.py validate --snippet-id <ID> --use-ollama

# Verify:
# - Ollama called (check logs)
# - CreateEntryAsync → CreateEntry
# - SaveAsync → Save
# - await removed
# - Status: verified
```

### Test 4: End-to-End Pilot (Small Scale)

**Purpose:** Verify entire pipeline on real content.

```bash
# Select small subset (5 pages)
python src/cli.py discover --family zip --max-pages 5
python src/cli.py validate --family zip --max-pages 5
python src/cli.py patch --family zip --dry-run
python src/cli.py report --family zip --format html

# Manual verification:
# 1. Open report.html
# 2. Check statistics look reasonable
# 3. Review 2-3 patches manually
# 4. Verify no database corruption: python src/cli.py db-status
```

### Test 5: Database Integrity

**Purpose:** Verify database constraints and relationships.

```bash
# Run integrity check
python src/cli.py db-check-integrity

# Expected checks:
# - All foreign keys valid
# - No orphaned records
# - Snippet counts match between pages and snippets tables
# - All snippet_versions reference valid snippets
# - All build_attempts reference valid versions
```

### Test 6: Telemetry Verification

**Purpose:** Verify events are logged correctly.

```bash
# Check local-telemetry integration
python src/cli.py validate --family zip --max-pages 1

# Verify in local-telemetry database:
sqlite3 C:\Users\prora\OneDrive\Documents\GitHub\local-telemetry\db\telemetry.db
> SELECT * FROM events WHERE source = 'example-reviewer' ORDER BY timestamp DESC LIMIT 10;

# Expected events:
# - validation_started
# - pattern_fix_applied
# - build_attempt
# - validation_completed
```

### Test 7: Rollback Capability

**Purpose:** Verify backups and rollback work.

```bash
# Apply patches
python src/cli.py patch --family zip --apply

# Trigger rollback
python src/cli.py rollback --run-id <RUN_ID>

# Verify:
# - Files restored from backups
# - Database marked patches as rolled-back
# - No data loss
```

---

## Success Metrics

### Pilot Success Criteria

1. **Coverage:** Process 100% of Aspose.ZIP snippets (1,401 expected)
2. **Validation Rate:** >60% snippets verified (compilable)
3. **Accuracy:** Pattern fixes have 0 false positives (manual spot-check 50 snippets)
4. **Safety:** 0 unintended changes to prose text or frontmatter
5. **Performance:** <5 seconds per snippet average (including Ollama)
6. **Reliability:** <1% failure rate (database corruption, crashes)

### Metrics to Track

- Total snippets discovered
- Snippets by status: unverified | verified | needs-fix | skipped
- Fixes by type: pattern | ollama | manual
- Compilation success rate: before fixes | after pattern fixes | after Ollama
- Time per snippet: discovery | validation | patching
- Error rate: by error category (CS0117, CS1061, etc.)
- LLM verification: formatting issues detected | auto-fixed | manual required

### Post-Pilot Assessment

**Qualitative:**
- Does the system correctly identify known issues?
- Are the fixes semantically correct (not just syntactically)?
- Does the system scale to other families (generic enough)?
- Is the database schema sufficient for tracking?
- Is the CLI intuitive for operators?

**Quantitative:**
- Time saved vs manual review (estimate 10 min/page manual, <1 min/page automated)
- ROI projection for all families (10,000+ snippets)
- Maintenance burden (config updates, pattern tuning)

---

## Dependencies (requirements.txt)

```txt
# Core
python>=3.8
sqlite3  # Built-in

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0  # For future schema migrations

# HTTP
requests>=2.31.0

# Markdown parsing
markdown-it-py>=3.0.0
python-frontmatter>=1.0.0

# Code analysis
regex>=2023.10.0

# Telemetry
python-json-logger>=2.0.0

# Reporting
jinja2>=3.1.0  # For HTML reports

# Testing (optional)
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

---

## Risk Mitigation

### Risk: False Positives in Pattern Fixes
**Mitigation:**
- All auto-applied fixes compile successfully before marking verified
- Manual spot-check of 50 random snippets during pilot
- Database tracks all fixes with before/after versions
- Rollback capability via backups

### Risk: Ollama Hallucinations
**Mitigation:**
- 3-attempt limit with progressively stricter prompts
- Always compile after Ollama fix (no blind acceptance)
- Non-existent API list provided in prompt
- Temperature set to 0.1 (low creativity)
- Response size limit (50KB max)

### Risk: Gist Update Failures
**Mitigation:**
- Gist files detected and handled separately
- Complex gists flagged for manual review
- Inline replacement only for simple snippets (<50 lines)
- Track gist updates in separate table (future)

### Risk: Translation Desynchronization
**Mitigation:**
- Compare code content across translations
- Auto-apply only if code identical
- Flag differing translations for manual review
- Track translation groups in database

### Risk: Database Corruption
**Mitigation:**
- SQLite WAL mode for crash resilience
- Single-writer pattern (no concurrent writes)
- Regular backups before patching
- Integrity checks in CLI

### Risk: Formatting Damage from Patching
**Mitigation:**
- LLM verification pass after patching
- Safety validation checklist (no frontmatter changes, etc.)
- Unified diff format with context
- Pre-patch backups for all files
- Rollback capability

---

## Timeline Estimate (Pilot)

**Setup (Day 1):**
- Create database schema: 2 hours
- Implement discovery service: 3 hours
- Implement snippet locator: 2 hours
- Setup telemetry integration: 1 hour
**Total:** 8 hours

**Validation Pipeline (Day 2-3):**
- Implement workspace manager: 3 hours
- Implement pattern registry: 4 hours
- Implement validation orchestrator: 5 hours
- Implement Ollama integration: 4 hours
**Total:** 16 hours

**Patching System (Day 4):**
- Implement patch generator: 4 hours
- Implement content patcher: 3 hours
- Implement LLM page verifier: 3 hours
- Implement safety validation: 2 hours
**Total:** 12 hours

**CLI and Reporting (Day 5):**
- Implement CLI interface: 4 hours
- Implement HTML report generation: 3 hours
- Implement database queries: 2 hours
**Total:** 9 hours

**Pilot Execution (Day 6-7):**
- Discovery run: 30 minutes
- Validation run (1,401 snippets @ 5 sec each): 2 hours
- Review and analysis: 2 hours
- Patching and verification: 1 hour
- Final report and documentation: 2 hours
**Total:** 7.5 hours

**Total Pilot Effort:** ~52.5 hours (~7 working days)

---

## Conclusion

This plan defines a **production-ready, generic system** for validating and fixing code examples across all Aspose product families. The pilot will:

1. ✅ Process all 1,401 Aspose.ZIP examples across 172 pages
2. ✅ Validate snippets by compiling against latest NuGet packages
3. ✅ Apply pattern-based fixes + Ollama auto-fixes
4. ✅ Generate safe patches with rollback capability
5. ✅ Track all operations in SQLite database
6. ✅ Integrate with local-telemetry for observability
7. ✅ Produce comprehensive HTML reports

**Extensibility:** The system is designed to scale to all Aspose families (Words, PDF, Cells, etc.) with minimal configuration changes.

**Next Step:** Approve this plan and begin implementation.

---

**Plan Status:** ✅ Ready for Review and Approval
**Author:** Claude (Sonnet 4.5)
**Date:** 2026-01-09
