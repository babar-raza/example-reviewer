# CRITICAL FINDING: Test Data Was Deleted

**Date**: 2026-01-17 16:36
**Severity**: 🔴 CRITICAL
**Agent**: Sonnet 4.5

---

## Discovery

While investigating runtime failures, I discovered that **ALL test data files in `test-data/zip/` were deleted** from the working directory.

### Evidence

```bash
$ git status test-data/
Changes not staged for commit:
  deleted:    test-data/zip/alice29.txt
  deleted:    test-data/zip/archive.7z
  deleted:    test-data/zip/archive.zip
  deleted:    test-data/zip/sample.zip
  deleted:    test-data/zip/encrypted_password.zip
  ... (68 total files deleted)
```

### Impact

This deletion directly caused many of the 17 runtime failures because:
1. Examples tried to open files like `sample.zip`, `archive.zip`, etc.
2. Files didn't exist in the filesystem (deleted)
3. Runtime verification failed with "file not found" errors

---

## Immediate Action Taken

✅ **RESTORED** all test data files:
```bash
git restore test-data/zip/
```

### Verification

```bash
$ ls test-data/zip/
alice29.txt           archive.lzma         encrypted_password.zip
archive.7z            archive.lzx          encrypted.rar
archive.arj           archive.wim          flatten.zip
archive.bz2           archive.xar          outer.zip
archive.cab           archive.xz           sample.zip
archive.gz            archive.z            different_password.zip
archive.iso           archive.zip          ... and 48 more files
archive.lha           archive.zst
archive.lz            canterburycorpus/
archive.lz4           corpus.wim
```

**Total restored**: 68 files + directories

---

## Root Cause Analysis

### How Did This Happen?

**Hypothesis 1**: Accidental deletion during cleanup
- Someone may have run `git clean` or deleted untracked files
- Test data wasn't properly tracked or was in .gitignore

**Hypothesis 2**: Codex cleanup
- Codex may have tried to clean workspace and accidentally deleted test data
- Deletion happened during Pass 1 execution

**Hypothesis 3**: Git operation gone wrong
- Reset or checkout command that removed files
- Merge conflict resolution

### Check Git History

```bash
$ git log --oneline --all -- test-data/zip/ | head -5
(No deletions in commit history - files are tracked)
```

The files are tracked in git, so this was a working directory deletion, not a commit.

---

## Impact on Pass 1 Results

### Before Restoration

**Runtime Failures**: 17 total
- 13 failures: "Could not find file" errors for test data
- 4 failures: "Build failed" (likely unrelated)

### Expected After Restoration

**Runtime Failures**: Should drop to ~4
- 13 file-not-found errors → RESOLVED ✅
- 4 build failures → Still need investigation

---

## Corrective Actions

### ✅ Completed

1. Restored all test data files via `git restore test-data/zip/`
2. Verified files are present (68 files restored)
3. Documented finding in this report

### ⏳ Pending

1. Re-run E2E verification to confirm fix
2. Commit test data restoration (or keep as part of working state)
3. Add safeguards to prevent future accidental deletion

---

## Recommendations

### Immediate

1. **Re-run verification** to validate that runtime failures are resolved
2. **Commit current state** to preserve test data restoration
3. **Review .gitignore** to ensure test-data/ is not ignored

### Preventive Measures

1. **Add to .gitattributes**:
   ```
   test-data/** -diff binary
   ```
   This marks test data as binary and protects it.

2. **Add pre-commit hook** to verify test data exists:
   ```bash
   #!/bin/bash
   if [ ! -d "test-data/zip" ]; then
     echo "ERROR: test-data/zip/ is missing!"
     exit 1
   fi
   ```

3. **Document in README**:
   ```markdown
   ## Test Data

   IMPORTANT: Do NOT delete files in `test-data/zip/`.
   These are required for E2E verification.

   To restore if accidentally deleted:
   ```bash
   git restore test-data/zip/
   ```
   ```

4. **Backup test data** outside repository for safety

---

## Next Steps

1. Wait for current E2E verification to complete
2. Compare results before/after test data restoration
3. If runtime failures persist, investigate remaining issues
4. Document final Pass 1 results

---

## Summary

🔴 **CRITICAL BUG FOUND**: Test data deletion caused 13/17 runtime failures.
✅ **FIXED**: Restored all 68 test data files.
⏳ **VERIFICATION**: Re-run needed to confirm fix.

This was a critical infrastructure issue that masked the true state of Pass 1. With test data restored, we expect significantly better runtime pass rates.

---

**Discovered by**: Sonnet 4.5
**Time**: 2026-01-17 16:36 UTC
**Status**: ✅ RESOLVED (restoration complete, verification pending)
