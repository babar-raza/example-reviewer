# Status Verification Plan: T10

**Task**: T10 - Verify All Snippet Statuses
**Agent**: C (Testing)
**Date**: 2026-01-12 15:05
**Status**: READY TO EXECUTE (after T9)

---

## Objective

Verify the final status of all 4 snippets after integration testing and mark snippet 140 with appropriate metadata.

---

## Verification Checklist

### Snippet 136: Using-Only Code

**Expected Status**: `verified`
**Expected Metadata**:
- `context_inferred`: TRUE
- `iterations`: 0-1
- `final_model`: None or 'qwen2.5-coder'

**Verification SQL**:
```sql
SELECT s.snippet_id, s.status, fs.context_inferred, fs.total_iterations, fs.final_status
FROM snippets s
LEFT JOIN fix_sessions fs ON s.snippet_id = fs.snippet_id
  AND fs.run_id = (SELECT MAX(run_id) FROM runs)
WHERE s.snippet_id = 136;
```

**Expected Result**:
```
snippet_id | status   | context_inferred | total_iterations | final_status
-----------|----------|------------------|------------------|-------------
136        | verified | 1                | 0-1              | success
```

**Pass Criteria**: Status = 'verified', context_inferred = 1 (TRUE)

---

### Snippet 138: Already Verified (Regression Check)

**Expected Status**: `verified` (NO CHANGE from Run 29)
**Expected Metadata**: Unchanged

**Verification SQL**:
```sql
SELECT s.snippet_id, s.status, s.updated_at,
       (SELECT COUNT(*) FROM build_attempts ba
        WHERE ba.snippet_id = 136
          AND ba.run_id = (SELECT MAX(run_id) FROM runs)) as attempts_in_last_run
FROM snippets s
WHERE s.snippet_id = 138;
```

**Expected Result**:
```
snippet_id | status   | updated_at          | attempts_in_last_run
-----------|----------|---------------------|----------------------
138        | verified | (pre-T9 timestamp)  | 0
```

**Pass Criteria**:
- Status = 'verified' (unchanged)
- No build attempts in latest run (not re-processed)
- updated_at timestamp BEFORE T9 execution

---

### Snippet 139: ASP.NET Core Minimal API

**Expected Status**: `verified`
**Expected Metadata**:
- `context_inferred`: FALSE (no context needed, has namespace/class)
- `iterations`: 2-3
- `final_model`: 'qwen2.5-coder'
- `models_tried`: ['qwen2.5-coder']

**Verification SQL**:
```sql
SELECT s.snippet_id, s.status, fs.total_iterations, fs.models_tried, fs.final_status
FROM snippets s
LEFT JOIN fix_sessions fs ON s.snippet_id = fs.snippet_id
  AND fs.run_id = (SELECT MAX(run_id) FROM runs)
WHERE s.snippet_id = 139;
```

**Expected Result**:
```
snippet_id | status   | total_iterations | models_tried        | final_status
-----------|----------|------------------|---------------------|-------------
139        | verified | 2-3              | ["qwen2.5-coder"]   | success
```

**Pass Criteria**:
- Status = 'verified'
- Iterations 2-3 (not >5)
- final_status = 'success'

---

### Snippet 140: Code Fragment (Unfixable)

**Current Status**: `needs-fix` (expected after T9)
**Action Required**: Mark with metadata explaining why unfixable

**Verification SQL**:
```sql
SELECT s.snippet_id, s.status, fs.total_iterations, fs.final_status, fs.models_tried
FROM snippets s
LEFT JOIN fix_sessions fs ON s.snippet_id = fs.snippet_id
  AND fs.run_id = (SELECT MAX(run_id) FROM runs)
WHERE s.snippet_id = 140;
```

**Expected Result**:
```
snippet_id | status    | total_iterations | final_status      | models_tried
-----------|-----------|------------------|-------------------|-------------------
140        | needs-fix | 3-10             | max_iterations OR | ["qwen2.5-coder"]
           |           |                  | infinite_loop     |
```

**Action**: Add metadata to document why unfixable

---

## Mark Snippet 140 as "Needs Manual Fix"

### Step 1: Add Notes Column (if not exists)

**Check if notes column exists**:
```sql
PRAGMA table_info(snippets);
```

**If notes column doesn't exist, add it**:
```sql
ALTER TABLE snippets ADD COLUMN notes TEXT;
```

### Step 2: Update Snippet 140 with Reason

**SQL Update**:
```sql
UPDATE snippets
SET notes = 'Unfixable: Code fragment depending on runtime context from previous snippet (app variable from snippet 139). Requires multi-snippet validation support (future feature).'
WHERE snippet_id = 140;
```

**Verify Update**:
```sql
SELECT snippet_id, status, notes
FROM snippets
WHERE snippet_id = 140;
```

**Expected Result**:
```
snippet_id | status    | notes
-----------|-----------|-----------------------------------------------
140        | needs-fix | Unfixable: Code fragment depending on runtime...
```

---

## Overall Success Metrics

### Target: 75% Success Rate (3/4 Snippets)

**Calculation**:
```
Verified Snippets: 136, 138, 139 = 3
Total Snippets: 4
Success Rate: 3/4 = 75% ✓
```

**Breakdown**:
| Snippet | Status | Reason |
|---------|--------|--------|
| 136 | ✅ verified | Context inference fix |
| 138 | ✅ verified | No regression (already fixed) |
| 139 | ✅ verified | ASP.NET patterns fix |
| 140 | ❌ needs-fix | Code fragment (unfixable) |

**Result**: TARGET MET ✓

---

## Regression Check: Other Snippets

**Scope**: Check if any OTHER snippets in the ZIP family changed status unexpectedly.

**Query**:
```sql
SELECT s.snippet_id, s.page_id, s.status,
       (SELECT relative_path FROM pages WHERE page_id = s.page_id) as page_path
FROM snippets s
WHERE s.family = 'zip'
  AND s.snippet_id NOT IN (136, 138, 139, 140)
  AND s.status = 'needs-fix'
  AND s.updated_at >= (SELECT started_at FROM runs WHERE run_id = (SELECT MAX(run_id) FROM runs));
```

**Expected Result**: Empty (no new failures)

**If NOT Empty**:
- **Action**: Investigate each snippet
- **Determine**: Is this a regression or expected?
- **Document**: In T10 issues report

---

## Verification Report Template

**File**: `reports/agents/integration/T10_verification_results.md`

```markdown
# T10 Verification Results

**Date**: 2026-01-12
**Run ID**: [latest run_id]

## Snippet Status Summary

| Snippet ID | Page | Status | Context Inferred | Iterations | Pass/Fail |
|------------|------|--------|------------------|------------|-----------|
| 136 | 60 | verified | TRUE | 0-1 | ✅ PASS |
| 138 | 60 | verified | - | - | ✅ PASS (no regression) |
| 139 | 60 | verified | FALSE | 2-3 | ✅ PASS |
| 140 | 60 | needs-fix | FALSE | 3-10 | ✅ EXPECTED (marked) |

## Success Rate Calculation

- **Target**: 75% (3/4 snippets)
- **Achieved**: 75% (3/4 snippets)
- **Status**: ✅ TARGET MET

## Snippet 140 Metadata

**Status**: needs-fix
**Reason**: Code fragment depending on runtime context (app variable)
**Notes**: Added to database
**Future Action**: Requires multi-snippet validation feature

## Regression Check

**Query Results**: [Empty / Issues Found]
**Status**: ✅ NO REGRESSIONS / ⚠️ ISSUES FOUND

## Acceptance Criteria

- [x] Snippet 136 verified with context inference
- [x] Snippet 138 remains verified (no regression)
- [x] Snippet 139 verified with ASP.NET patterns
- [x] Snippet 140 marked with notes
- [x] 75% success rate achieved
- [x] No unexpected regressions

## Conclusion

T10 verification complete. All acceptance criteria met.
```

---

## Acceptance Criteria

- [ ] All 4 snippet statuses verified
- [ ] Snippet 136: verified with context_inferred = TRUE
- [ ] Snippet 138: verified with no regression
- [ ] Snippet 139: verified with 2-3 iterations
- [ ] Snippet 140: marked with unfixable reason
- [ ] Success rate: 75% (3/4) ✓
- [ ] No unexpected regressions found
- [ ] Verification report created

---

## Next Steps

After T10 complete:
1. **T11**: Edge case testing (optional - full validation on ZIP family)
2. **T12**: Update documentation (`docs/validation.md`, `docs/architecture.md`)
3. **T13**: Create fix summary document

---

**Agent C Status**: BLOCKED - Waiting for T9 completion
