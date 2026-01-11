# API Reference

## Command-Line Interface

### Global Options
```bash
python src/cli.py <command> [options]
```

---

## Commands

### `init-db`
Initialize or migrate database schema.

**Usage:**
```bash
python src/cli.py init-db
```

**Description:**
- Creates database at `data/examples.db`
- Applies schema migrations (creates gist tables if missing)
- Idempotent (safe to run multiple times)
- Required before first use or after schema updates

**Output:**
```
[*] Initializing database...
[OK] Database initialized successfully
[i] Database location: data/examples.db
```

**Schema Versions:**
- Version 1: Core tables (pages, snippets, versions, runs)
- Version 2: Gist tables (gists, gist_files)

---

### `discover`
Scan markdown files and extract code snippets (including gists).

**Usage:**
```bash
python src/cli.py discover --family <family> [--max-pages N]
```

**Required Arguments:**
- `--family <family>`: Product family to scan (e.g., `zip`, `words`)

**Optional Arguments:**
- `--max-pages N`: Limit number of pages to process (default: unlimited)

**Description:**
- Scans markdown files for specified family
- Extracts fenced code blocks (` ```csharp ... ``` `)
- **Fetches GitHub Gists** and stores real code (not shortcode)
- Persists snippets to database
- Creates discovery report

**Gist Behavior:**
- Parses gist shortcodes: `{{< gist "user" "id" "file.cs" >}}`
- Fetches content from GitHub API (with caching)
- Stores fetched code in `snippet_versions.code_content`
- Skips non-C# gists with recorded reason
- Handles ambiguous multi-file gists (skip with reason)

**Example:**
```bash
# Discover all zip examples
python src/cli.py discover --family zip

# Discover first 20 pages
python src/cli.py discover --family zip --max-pages 20
```

**Output:**
```
[*] Starting discovery for family: zip
[i] Run ID: 42
[i] Artifacts directory: artifacts/runs/run-042
[i] Fetching gist abc123 from GitHub...
[OK] Gist fetched: Example.cs
[i] Skipping gist xyz789: ambiguous (multiple .cs files)

[OK] Discovery completed
[i] Pages found: 150
[i] Pages processed: 150
[i] Snippets found: 523
[i] Errors: 0
```

**Files Created:**
- `artifacts/runs/run-XXX/discovery_report.json`
- `cache/gists/<gistid>.json` (API responses)
- `cache/gists/<gistid>/<filename>.raw` (file content)

---

### `validate`
Compile and validate discovered snippets.

**Usage:**
```bash
python src/cli.py validate --family <family> [--max-snippets N] [--no-ollama]
```

**Required Arguments:**
- `--family <family>`: Product family to validate

**Optional Arguments:**
- `--max-snippets N`: Limit number of snippets to validate
- `--no-ollama`: Disable Ollama LLM fixes (pattern-based only)

**Description:**
- Compiles each snippet in isolated workspace
- Applies pattern-based fixes for common errors
- Optionally uses Ollama for intelligent fixes
- Updates snippet status: `verified`, `needs-fix`, `skipped`

**Gist Validation:**
- Uses **fetched code** from discovery (not shortcode)
- Validation identical to fenced code blocks
- Skip reasons preserved from discovery

**Example:**
```bash
# Validate all zip snippets
python src/cli.py validate --family zip

# Validate first 50 snippets, no LLM
python src/cli.py validate --family zip --max-snippets 50 --no-ollama
```

**Output:**
```
[*] Starting validation for family: zip
[i] Validating snippet 1/523 (fence)
[OK] Compiled successfully
[i] Validating snippet 2/523 (gist)
[!] Compilation failed: CS0103
[i] Applying pattern fix: missing using
[OK] Fixed and verified

[OK] Validation completed
[i] Verified: 480
[i] Needs fix: 12
[i] Skipped: 31
```

---

### `patch`
Apply verified code to original markdown files.

**Usage:**
```bash
python src/cli.py patch --family <family> [--dry-run] [--gist-mode MODE]
```

**Required Arguments:**
- `--family <family>`: Product family to patch

**Optional Arguments:**
- `--dry-run`: Preview changes without modifying files (default: false)
- `--gist-mode MODE`: How to handle gists (see below)

**Gist Modes:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `inline-on-change` | Replace only changed gists (default) | Standard workflow |
| `preserve` | Never replace gists (keep shortcodes) | Validation-only |
| `inline-always` | Replace all gists (even unchanged) | Migrate to inline |

**Description:**
- Reads verified snippets from database
- **Fences**: Replaces code within fence markers
- **Gists**: Follows gist-mode rules (see [patching-strategies.md](patching-strategies.md))
- Preserves file structure, line endings, formatting

**Gist Patching Logic:**
```
For each verified gist:
  IF mode == 'preserve':
    Keep gist shortcode (no change)
  ELSE IF mode == 'inline-on-change':
    IF code_unchanged:
      Keep gist shortcode
    ELSE:
      Replace with inline ```csharp fence
  ELSE IF mode == 'inline-always':
    Always replace with inline ```csharp fence
```

**Examples:**
```bash
# Dry run (preview changes)
python src/cli.py patch --family zip --dry-run

# Patch with default gist mode (inline-on-change)
python src/cli.py patch --family zip

# Preserve all gist shortcodes (validation-only)
python src/cli.py patch --family zip --gist-mode preserve

# Inline all gists (migration mode)
python src/cli.py patch --family zip --gist-mode inline-always
```

**Output:**
```
[*] Patching family: zip
[i] Gist mode: inline-on-change
[i] Patching snippet 1/480 (fence)
[OK] Patched: content/docs.aspose.net/zip/net/example.md
[i] Patching snippet 2/480 (gist)
[i] Gist verified; unchanged; no patch needed
[i] Patching snippet 3/480 (gist)
[OK] Gist inlined: shortcode replaced with verified code fence

[OK] Patching completed
[i] Files modified: 89
[i] Patches applied: 95
[i] Gists unchanged: 12
[i] Gists inlined: 3
[i] Errors: 0
```

**Dry Run Output:**
```
[DRY RUN] Would modify: content/docs.aspose.net/zip/net/example.md
[DRY RUN] Would inline gist: abc123 in example2.md
[DRY RUN] Gist unchanged (would preserve): xyz789
```

---

### `db-status`
Display database statistics.

**Usage:**
```bash
python src/cli.py db-status [--family <family>]
```

**Optional Arguments:**
- `--family <family>`: Show stats for specific family only

**Example:**
```bash
# Overall stats
python src/cli.py db-status

# Family-specific stats
python src/cli.py db-status --family zip
```

**Output:**
```
[*] Database Status
[i] Database: data/examples.db
[i] Family: zip

Pages: 150
Snippets: 523
  - Verified: 480
  - Unverified: 12
  - Needs fix: 0
  - Skipped: 31
```

---

### `check-ollama`
Verify Ollama availability and model selection.

**Usage:**
```bash
python src/cli.py check-ollama
```

**Description:**
- Checks if Ollama is running
- Verifies code model availability
- Shows selected model for LLM fixes

**Example:**
```bash
python src/cli.py check-ollama
```

**Output:**
```
[*] Checking Ollama...
[OK] Ollama is available
[OK] Selected model: qwen2.5-coder
```

---

## Environment Variables

### GITHUB_TOKEN
**Purpose:** Increase GitHub API rate limits for gist fetching.

**Set Before Discovery:**
```bash
# Linux/Mac
export GITHUB_TOKEN="ghp_your_token_here"

# Windows
set GITHUB_TOKEN=ghp_your_token_here
```

**Rate Limits:**
- Without token: 60 requests/hour
- With token: 5,000 requests/hour

**See:** [configuration.md](configuration.md) for details.

---

## Workflow Examples

### Standard Workflow (with Gists)
```bash
# 1. Initialize database
python src/cli.py init-db

# 2. Set GitHub token (optional but recommended)
export GITHUB_TOKEN="ghp_..."

# 3. Discover snippets (fetches gists)
python src/cli.py discover --family zip

# 4. Validate snippets
python src/cli.py validate --family zip

# 5. Preview patches
python src/cli.py patch --family zip --dry-run

# 6. Apply patches (default: inline changed gists)
python src/cli.py patch --family zip

# 7. Commit changes
git add .
git commit -m "Verified zip examples (including gists)"
```

### Validation-Only Workflow
```bash
# Validate gists without modifying markdown
python src/cli.py discover --family zip
python src/cli.py validate --family zip
python src/cli.py patch --family zip --gist-mode preserve --dry-run
```

### Migration Workflow (Gist → Inline)
```bash
# Convert all gists to inline fences
python src/cli.py discover --family zip
python src/cli.py validate --family zip
python src/cli.py patch --family zip --gist-mode inline-always
```

### Limited Scope Test
```bash
# Test on small subset
python src/cli.py discover --family zip --max-pages 5
python src/cli.py validate --family zip --max-snippets 20
python src/cli.py patch --family zip --dry-run
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (check output for details) |

---

## Output Files

### Discovery
- `artifacts/runs/run-XXX/discovery_report.json`: Statistics and metrics
- `cache/gists/<gistid>.json`: GitHub API responses (cached)
- `cache/gists/<gistid>/<filename>.raw`: Gist file content

### Validation
- `artifacts/runs/run-XXX/validation_report.json`: Validation results
- `artifacts/runs/run-XXX/build_logs/`: Compilation outputs

### Patching
- Modified `.md` files in content directories
- `artifacts/runs/run-XXX/patch_report.json`: Patch results

---

## Database Schema

### Gist Tables (Version 2)

**gists:**
```sql
CREATE TABLE gists (
    gist_id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    description TEXT,
    updated_at TEXT,
    etag TEXT,
    last_fetched_at TEXT,
    last_status TEXT,  -- 'success', 'not_found', 'rate_limited', 'error'
    last_error TEXT
);
```

**gist_files:**
```sql
CREATE TABLE gist_files (
    gist_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    raw_url TEXT NOT NULL,
    language TEXT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    file_size INTEGER,
    fetched_at TEXT,
    PRIMARY KEY (gist_id, filename)
);
```

---

## Troubleshooting

### Gists Not Fetching
```bash
# Check token
echo $GITHUB_TOKEN

# Check network
curl https://api.github.com/rate_limit

# Check database for errors
sqlite3 data/examples.db "SELECT * FROM gists WHERE last_status != 'success';"
```

### Validation Failures
```bash
# Check build logs
ls artifacts/runs/run-XXX/build_logs/

# Re-validate with Ollama disabled
python src/cli.py validate --family zip --no-ollama
```

### Patching Errors
```bash
# Always dry-run first
python src/cli.py patch --family zip --dry-run

# Check for file permission issues
ls -la content/docs.aspose.net/zip/
```

---

**See Also:**
- [architecture.md](architecture.md) - System design
- [configuration.md](configuration.md) - Environment setup
- [patching-strategies.md](patching-strategies.md) - Detailed patching rules
