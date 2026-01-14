# Example Reviewer System Architecture

## Overview

The Example Reviewer system validates and patches code examples in markdown documentation. It supports both **fenced code blocks** and **GitHub Gists** for C# code validation.

## Core Components

### 1. Discovery Service (`discovery_service.py`)
Scans markdown files and extracts code snippets for validation.

**Supported Snippet Types:**
- **Fenced Code Blocks**: ` ```csharp ... ``` ` (inline in markdown)
- **GitHub Gists**: `{{< gist "user" "gistid" "file.cs" >}}` (Hugo shortcode)

**Gist Pipeline Branch** (Phase 1):
```
Markdown File with Gist Shortcode
  │
  ├─→ Parse shortcode (extract gist_id, owner, filename)
  │
  ├─→ Fetch from GitHub API (with caching + ETag support)
  │     └─→ cache/gists/<gistid>.json (metadata)
  │     └─→ cache/gists/<gistid>/<filename>.raw (content)
  │
  ├─→ Select C# file:
  │     ├─→ Explicit filename specified → use that file
  │     ├─→ Single .cs/.csx file → auto-select
  │     └─→ Multiple .cs files → mark ambiguous (skip)
  │
  ├─→ Persist to database:
  │     ├─→ gists table (metadata, ETag, fetch status)
  │     └─→ gist_files table (content, hash, language)
  │
  └─→ Store REAL code as snippet content (not shortcode)
```

**Fence Pipeline** (Standard):
```
Markdown File with Fence
  │
  ├─→ Extract code between fence markers
  │
  └─→ Store directly in snippet_versions table
```

### 2. Validation Orchestrator (`validation_orchestrator.py`)
Compiles and validates extracted code snippets.

- Gist snippets validate with **actual fetched code** (not shortcode text)
- Same validation rules apply to both fences and gists
- Skip rules:
  - Non-C# language
  - Empty/trivial code
  - Package manager commands
  - ASCII art

### 3. Patching Service (`patching_service.py`)
Updates markdown files with verified code.

**Fence Patching:**
- Replaces code within existing fence markers
- Preserves language marker and fence style

**Gist Patching** (Phase 1):
```
For each verified gist snippet:
  │
  ├─→ Compare original vs verified code hash
  │
  ├─→ If UNCHANGED:
  │     └─→ Keep gist shortcode (no modification)
  │
  └─→ If CHANGED:
        └─→ Replace shortcode with inline fence:
              ```csharp
              <verified_code>
              ```
```

**Gist Patching Modes:**
- `preserve`: Never replace gists (always keep shortcode)
- `inline-on-change`: Replace only changed gists (default)
- `inline-always`: Replace all gists with inline fences

### 4. Database Layer (`database.py`)
SQLite database with WAL mode for persistence.

**Gist-Specific Tables:**
- `gists`: Gist metadata (id, owner, description, ETag, fetch status)
- `gist_files`: Individual files within gists (content, hash, language)

### 5. Gist Service (`gist_service.py`)
Handles GitHub Gist API integration.

**Features:**
- Public GitHub Gist API (no auth required)
- Optional `GITHUB_TOKEN` for higher rate limits (60/hr → 5000/hr)
- Disk caching with ETag support
- Rate limit detection and retry logic
- Smart C# file selection

## Data Flow

### Discovery Flow (with Gist)
```
1. Scan markdown files (discovery_service.py)
2. Parse gist shortcode
3. Fetch gist from GitHub API or cache (gist_service.py)
4. Store gist metadata in database (database.py)
5. Store REAL code in snippet_versions table
6. Preserve original shortcode in locator notes
```

### Validation Flow
```
1. Get snippets with status='unverified' (database.py)
2. Extract code from snippet_versions.code_content
   (For gists: this is the FETCHED code, not shortcode)
3. Compile in isolated workspace (workspace_manager.py)
4. If compilation fails, attempt LLM-based fixes (persistent_fix_service.py)
5. If compilation succeeds, track verified candidate (don't return yet)
6. Runtime validation (Stage 4.5) - if enabled:
   - Execute compiled code in isolated subprocess
   - Capture stdout, stderr, exceptions, exit code
   - Store execution_results in database
   - Strict mode: downgrade to 'needs-fix' on failure
   - Lenient mode: keep 'verified' with warnings
7. Patching (Stage 4.6) - only if status is still 'verified':
   - Apply verified code to markdown file
   - Skip if runtime validation failed in strict mode
8. Update snippet status and finalize
```

### Persistent Fix Service (`persistent_fix_service.py`)

The Persistent Fix Service provides iterative LLM-based code fixing with context inference and model fallback.

**Features:**
- Up to 10 fix iterations per snippet
- Context inference for partial code snippets
- Model fallback after 3 consecutive failures
- Infinite loop detection (stops if same error repeats 3 times)
- Immediate patching on successful fix

**Fix Flow:**
```
1. Check if code needs context wrapping (_needs_context method)
2. If needed, infer context from nearby snippets
3. Compile code and collect errors
4. Send code + errors to LLM for fixing
5. Repeat until success or max iterations
6. Extract fixed portion if context was added
7. Trigger immediate patching callback
```

#### Context Inference

Context inference wraps partial code snippets (methods, fields without class/namespace) with minimal compilable structure.

**Detection Algorithm** (`_needs_context` method):
```python
1. Check for namespace declaration → if present, no context needed
2. Check for class/interface/struct/enum → if present, no context needed
3. Check for using-only code:
   - Strip using statements and comments
   - If nothing remains → needs context (wrapping required)
4. Check for methods or fields → needs context
5. Otherwise → no context needed (code is complete)
```

**Using-Only Code Detection** (Added 2026-01-12):
- Code containing only `using` statements with comments/whitespace
- Detected by stripping using statements + comments, checking if empty
- Example:
  ```csharp
  using Aspose.Zip;                 // Archive, ArchiveEntry
  using Aspose.Zip.Saving;          // DeflateCompressionSettings
  ```
  ↓ After stripping → empty → needs context ✓

**Context Wrapping Process:**
```
Original partial code:
    public void DoWork() { /* code */ }

After wrapping:
    using System;
    namespace TempNamespace {
        class TempClass {
            public void DoWork() { /* code */ }
        }
    }

After compilation + extraction:
    public void DoWork() { /* fixed code */ }
```

**Context Extraction:**
- Query nearby snippets (same page, within ±2 ordinal positions)
- Extract using statements, namespace, class declarations
- Build complete compilable code
- After successful compilation, extract only the fixed portion
- Verify extracted code compiles standalone

**Metadata Tracking:**
- `fix_sessions.context_inferred` = TRUE when context was added
- Stored in database for analysis and debugging

### Patching Flow (with Gist)
```
1. Get snippets with status='verified' (database.py)
2. For gist snippets:
   a. Compare original_hash vs verified_hash
   b. If unchanged: skip (keep shortcode)
   c. If changed: locate shortcode in markdown
   d. Replace with inline fence (```csharp)
3. Write modified markdown file
```

## Skip Reasons

Gists may be skipped during discovery for:
- **No C# files**: Gist contains only non-C# files
- **Ambiguous**: Multiple .cs files, no filename specified
- **Fetch error**: Network failure, rate limit, 404
- **Validation criteria**: Code doesn't meet C# snippet requirements

All skip reasons are persisted in database and reportable.

## Cache Strategy

**Gist Cache Location:** `cache/gists/`

**Cache Structure:**
```
cache/gists/
  ├── <gistid>.json          # API response with ETag
  └── <gistid>/
      └── <filename>.raw     # File content
```

**Cache Validity:**
- ETags used for conditional requests (`If-None-Match`)
- Cache checked before API call
- Fresh cache (< 1 hour) used directly
- Stale cache triggers conditional request (304 = still valid)

## Configuration

See [configuration.md](configuration.md) for environment variables and settings.

## Patching Strategies

See [patching-strategies.md](patching-strategies.md) for detailed gist replacement rules.
