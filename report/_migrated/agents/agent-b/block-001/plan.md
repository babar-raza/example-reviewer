# Agent B Plan: BLOCK-001 CLI Path Resolution Fix

**Task**: Fix CLI path resolution bug discovered during HARD-001
**Priority**: P0 EMERGENCY
**Estimated Time**: 5-10 minutes

---

## Context

Agent C discovered during HARD-001 E2E testing that the CLI's path resolution is broken:

```python
# Current (WRONG):
self.script_dir = Path(__file__).parent.parent  # Repo root
self.repo_root = self.script_dir.parent.parent  # BUG: Goes up 2 MORE levels
```

This causes config_dir and content_dir to point OUTSIDE the repository, breaking all testing.

---

## Implementation Steps

### Step 1: Verify Current Broken State
```bash
cd src
python -c "from cli import ExamplesReviewerCLI; cli = ExamplesReviewerCLI(); print('repo_root:', cli.repo_root); print('config_dir:', cli.config_dir)"
```

Expected (WRONG) output:
- repo_root: C:\Users\prora\OneDrive\Documents
- config_dir: C:\Users\prora\OneDrive\Documents\config\families

### Step 2: Apply Fix

**File**: src/cli.py
**Line**: 29

Change:
```python
self.repo_root = self.script_dir.parent.parent
```

To:
```python
self.repo_root = self.script_dir
```

### Step 3: Verify Fixed State
```bash
cd src
python -c "from cli import ExamplesReviewerCLI; cli = ExamplesReviewerCLI(); print('repo_root:', cli.repo_root); print('config_dir:', cli.config_dir)"
```

Expected (CORRECT) output:
- repo_root: C:\Users\prora\OneDrive\Documents\GitHub\example-reviewer
- config_dir: C:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\config\families

### Step 4: Create Unit Test

**File**: tests/test_cli_paths.py (NEW)

```python
import pytest
from pathlib import Path
from src.cli import ExamplesReviewerCLI


def test_cli_path_resolution():
    """Verify CLI paths point to correct locations within repository."""
    cli = ExamplesReviewerCLI()

    # repo_root should be the example-reviewer directory
    assert cli.repo_root.name == "example-reviewer"

    # config_dir should be inside repo
    assert cli.repo_root in cli.config_dir.parents
    assert cli.config_dir == cli.repo_root / "config" / "families"

    # content_dir should be inside repo
    assert cli.repo_root in cli.content_dir.parents
    assert cli.content_dir == cli.repo_root / "content"

    # All paths should exist or be creatable
    assert cli.repo_root.exists()
```

### Step 5: Run Unit Test
```bash
pytest tests/test_cli_paths.py -v
```

Expected: PASSED

### Step 6: Functional Test
Move Agent C's test files to correct locations and verify discovery works:

```bash
# Move test config to correct location
mv "C:\Users\prora\OneDrive\Documents\config\families\test.json" config/families/test.json

# Move test content to correct location
mkdir -p content/blog.aspose.net/test
mv "C:\Users\prora\OneDrive\Documents\content\blog.aspose.net\test\gist-test.md" content/blog.aspose.net/test/gist-test.md

# Run discovery
cd src
python cli.py discover --family test --max-pages 1
```

Expected: Discovery runs without "config not found" errors

### Step 7: Write Evidence

**File**: reports/agents/agent-b/block-001/evidence.md

Include:
- Before/after path verification output
- Git diff showing one-line change
- Unit test results
- Functional test output (discovery run)
- Confirmation that Agent C can resume

---

## Acceptance Criteria

- [x] repo_root points to repository root
- [x] config_dir points to <repo>/config/families/
- [x] content_dir points to <repo>/content/
- [x] Unit test created and passing
- [x] Functional test (discovery) works with correct paths
- [x] Test files moved to correct locations
- [x] Evidence file written with verification outputs

---

## Risks

**Risk**: NONE - This is a clear bug with obvious fix
**Regression**: Minimal - current code doesn't work, fix makes it work

---

## Next Steps After Completion

1. Route evidence to Orchestrator
2. Orchestrator unblocks HARD-001
3. Agent C resumes E2E testing with proper paths
4. All future testing can use standard repository structure

---

**Execute immediately - this blocks all other work**
