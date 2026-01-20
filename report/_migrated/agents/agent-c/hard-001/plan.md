# Agent C: End-to-End Smoke Test (HARD-001)

**Agent**: Agent C (Tests & Verification)
**Task ID**: HARD-001
**Priority**: P0 (BLOCKING)
**Started**: 2026-01-11

---

## Task Summary

Prove gist support works end-to-end with real GitHub API. Create minimal test configuration, fetch a real gist, verify cache and database, demonstrate patch workflow.

---

## Assumptions to Verify

1. **ASSUMPTION**: GitHub API public gists work without auth
   - **VERIFICATION**: Fetch a known public gist (e.g., aspose-* organization)
   - **EVIDENCE**: HTTP 200 response, valid JSON

2. **ASSUMPTION**: cache/gists/ auto-creates with proper permissions
   - **VERIFICATION**: Run discover, check directory exists
   - **EVIDENCE**: ls -la cache/gists/ output

3. **ASSUMPTION**: Database handles gist inserts without errors
   - **VERIFICATION**: Query gists and gist_files tables after fetch
   - **EVIDENCE**: SQL query results

4. **ASSUMPTION**: Patch dry-run shows correct replacement logic
   - **VERIFICATION**: Run patch --dry-run, check output
   - **EVIDENCE**: Patch preview showing gist → inline replacement

---

## Implementation Steps

### Step 1: Create Test Family Config

**File**: `config/families/test.json`

**Content**:
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

**Rationale**: Use Newtonsoft.Json (simple, stable) instead of Aspose packages to avoid complexity

### Step 2: Find Real Public Gist

**Search**: Look for public C# gist from known organization (aspose, microsoft, etc.)

**Method**:
- Search GitHub gists: `site:gist.github.com aspose c#`
- Verify gist is public and has single .cs file
- Extract gist ID and owner

**Fallback**: Create minimal test gist if needed (but prefer existing)

### Step 3: Create Test Content

**File**: `test-content/gist-smoke.md`

**Content**:
```markdown
---
title: Gist Smoke Test
---

# Test Gist Integration

This tests gist fetching from GitHub API.

{{< gist "username" "gistid" "Example.cs" >}}

End of test.
```

**Note**: Replace username/gistid with real values from Step 2

### Step 4: Run Discovery

**Command**:
```bash
cd src
PYTHONPATH="C:\Users\prora\AppData\Roaming\Python\Python313\site-packages" python cli.py discover --family test --max-pages 1
```

**Expected Output**:
- "Starting discovery for family: test"
- Gist fetch log message
- Success message
- No errors

**Evidence Capture**: Redirect to file or copy full output

### Step 5: Verify Cache Directory

**Commands**:
```bash
ls -la cache/gists/
cat cache/gists/<gistid>.json | head -20
ls -la cache/gists/<gistid>/
```

**Expected**:
- cache/gists/<gistid>.json exists
- JSON contains etag, cached_at, files
- cache/gists/<gistid>/<filename>.raw exists
- Raw file contains C# code

### Step 6: Verify Database Entries

**Commands**:
```bash
PYTHONPATH="C:\Users\prora\AppData\Roaming\Python\Python313\site-packages" python -c "import sqlite3; conn = sqlite3.connect('data/examples.db'); cursor = conn.cursor(); cursor.execute('SELECT * FROM gists'); print('GISTS:', cursor.fetchall()); cursor.execute('SELECT gist_id, filename, language, content_hash FROM gist_files'); print('GIST_FILES:', cursor.fetchall())"
```

**Expected**:
- gists table: 1 row with gist_id, owner, last_status='success'
- gist_files table: 1 row with filename, content, content_hash

### Step 7: Run Patch Dry-Run

**Command**:
```bash
cd src
PYTHONPATH="C:\Users\prora\AppData\Roaming\Python\Python313\site-packages" python cli.py patch --family test --dry-run
```

**Expected Output**:
- Patch preview showing original gist shortcode
- Decision: "unchanged" (no patch) OR "changed" (inline replacement)
- No actual file modification

---

## Tests to Add

**File**: `tests/test_e2e_smoke.py`

```python
"""
End-to-end smoke test for gist support.
Requires real GitHub API access (no auth needed for public gists).
Mark as slow test.
"""
import pytest
import subprocess
from pathlib import Path

@pytest.mark.slow
def test_gist_e2e_smoke():
    """Test complete discover → verify → patch workflow with real gist."""
    # This test runs actual CLI commands
    result = subprocess.run(
        ['python', 'src/cli.py', 'discover', '--family', 'test', '--max-pages', '1'],
        capture_output=True, text=True
    )

    assert result.returncode == 0
    assert 'gist' in result.stdout.lower()  # Gist processing mentioned

    # Verify cache created
    cache_dir = Path('cache/gists')
    assert cache_dir.exists()
    assert len(list(cache_dir.glob('*.json'))) > 0

    # Verify database entry
    import sqlite3
    conn = sqlite3.connect('data/examples.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM gists WHERE last_status = "success"')
    count = cursor.fetchone()[0]
    assert count > 0, "No successful gist fetches in database"
```

---

## Acceptance Checklist

- [ ] Test family config created (config/families/test.json)
- [ ] Test content created with real gist (test-content/gist-smoke.md)
- [ ] Discovery command runs successfully
- [ ] Cache directory exists (cache/gists/)
- [ ] Cache JSON file exists and valid
- [ ] Cache raw file exists with C# code
- [ ] Database gists entry created
- [ ] Database gist_files entry created
- [ ] Patch dry-run runs without errors
- [ ] E2E smoke test added (tests/test_e2e_smoke.py)
- [ ] Evidence file complete with all command outputs

---

## Rollback Plan

If E2E fails:
1. Document failure in evidence.md with error details
2. Keep test files for debugging
3. Escalate to Orchestrator with specific failure mode
4. Do NOT merge until resolved

If partial success:
1. Document what works and what doesn't
2. File specific issues for failures
3. Proceed with integration tests if discovery works

---

## Evidence Requirements

Must capture in `evidence.md`:
1. Full discover command output
2. Cache directory listing
3. Cache JSON content (first 50 lines)
4. Cache raw file content (first 20 lines)
5. Database query results
6. Patch dry-run output
7. Any errors encountered
8. Screenshots if helpful

---

**Status**: Ready to execute
**Next**: Run steps 1-7 and capture evidence
