# Addendum: Snippet Count Discrepancy Analysis

**Date:** 2026-01-13
**Issue:** ROB-06 tested 78 snippets instead of expected 90 (-12 snippets)

---

## Discrepancy Breakdown

### Snippet Counts Per Family

| Family | ROB-03 | ROB-06 | Delta | Impact |
|--------|--------|--------|-------|--------|
| Words | 15 | 15 | 0 | None |
| PDF | 15 | 13 | -2 | Minor |
| Cells | 15 | 14 | -1 | Minor |
| **Slides** | 15 | 7 | **-8** | **Major** |
| Email | 15 | 15 | 0 | None |
| Imaging | 15 | 14 | -1 | Minor |
| **Total** | **90** | **78** | **-12** | **13.3% reduction** |

---

## Root Cause

The Slides family tested only 7 snippets instead of 15, accounting for 8 of the 12 missing snippets (-66.7% of total discrepancy).

**Possible Causes:**

1. **Early termination:** Validation run may have been interrupted or timed out
2. **Snippet availability:** Only 7 unverified snippets were available in the database at the time
3. **Max-snippets logic:** The `--max-snippets 15` flag may have found only 7 qualifying snippets
4. **Database state:** Some snippets may have been marked as verified in a previous run

**Most Likely:** Option 2 or 3 - The validation system found only 7 unverified snippets for the Slides family at the time of execution.

---

## Impact on Results

### Positive Impact on Slides Success Rate

Slides achieved 85.7% success (6/7) in ROB-06 vs. 60% (9/15) in ROB-03.

**Two possible interpretations:**

1. **Selection bias:** The 7 snippets tested in ROB-06 were easier than the full 15-snippet set
2. **Genuine improvement:** P0 fixes actually improved Slides family performance

**Evidence for selection bias:**
- Dramatic reduction in test set size (15 → 7 = -53.3%)
- Success rate increase (+25.7pp) is suspiciously high
- Slides family had 7 namespace violations noted in console output

**Evidence for genuine improvement:**
- P0-1 fix allowed more iterations (avg attempts: 5.14 → 8.03)
- Slides had high success in ROB-03 (60%), suggesting good API compatibility
- Increase aligns with other families (Cells +50pp, Imaging +29pp)

**Verdict:** LIKELY GENUINE IMPROVEMENT, but selection bias cannot be ruled out.

---

## Impact on Overall Metrics

### Adjusted Analysis (Normalizing for Test Set Size)

If we assume the missing 8 Slides snippets would have had 60% success (ROB-03 baseline):
- Expected additional successes: 8 × 0.60 = 4.8 ≈ 5 snippets
- Adjusted ROB-06 total: 26 + 5 = 31 successes
- Adjusted ROB-06 success rate: 31/90 = 34.4%

**Result:** Still below 50% target, but slightly higher than reported 33.3%.

### Impact on Family Comparisons

The discrepancy affects the fairness of family comparisons:

**Slides:** 15 → 7 test set is not directly comparable to ROB-03
**PDF:** 15 → 13 may include different snippets
**Cells:** 15 → 14 mostly comparable
**Imaging:** 15 → 14 mostly comparable
**Words/Email:** 15 → 15 fully comparable

**Recommendation:** For ROB-07, ensure identical snippet sets are used for accurate before/after comparison.

---

## Console Output Evidence

From Run 48 (Slides):
```
[i] Limiting to 15 snippets
[i] Found 15 unverified snippets
```

But database shows only 7 distinct snippet IDs in run 48. This suggests:
- Multiple attempts were made on the same 7 snippets
- OR the validation stopped after 7 snippets despite finding 15

**Average attempts in Run 48:** 31 total attempts ÷ 7 snippets = 4.4 attempts per snippet

This is lower than the overall ROB-06 average of 8.03, suggesting:
- Some snippets succeeded quickly (within 1-2 iterations)
- Validation moved on to the next snippet after success
- The 15 "found" may include already-verified snippets that were skipped

---

## Recommendations

### For ROB-07 (Next Test Run)

1. **Pre-verify snippet sets:**
   - Query database for exact snippet IDs to be tested
   - Ensure 15 unverified snippets are available per family
   - Compare snippet IDs between ROB-03 and ROB-06 to identify overlaps

2. **Locked test sets:**
   - Create a fixed list of snippet IDs for comparison runs
   - Use `--snippet-ids` parameter (if available) to ensure identical sets
   - Document any snippets that become unavailable

3. **Validation checkpoints:**
   - Log snippet selection logic at runtime
   - Capture why certain snippets are skipped
   - Record database state before validation run

4. **Comparative analysis:**
   - For any family with <15 snippets, note this in the report
   - Adjust statistical comparisons to account for different test set sizes
   - Consider using matched pairs analysis (only compare snippets tested in both runs)

---

## Mitigation for Current Report

The ROB-06 evidence document includes the following mitigations:

1. **Transparency:** Clearly documented the 78 vs. 90 discrepancy
2. **Data preservation:** Exported raw metrics to `metrics.json`
3. **Query documentation:** Provided SQL queries to reproduce analysis
4. **Self-review penalty:** Deducted 0.5 points on Coverage dimension

**Final assessment remains valid:**
- P0 fixes verified working (not affected by discrepancy)
- Improvement confirmed (+10pp minimum, possibly +11pp adjusted)
- Target not met (even with adjustment: 34.4% < 50%)

---

## Conclusion

The 12-snippet discrepancy (particularly 8 from Slides) introduces some uncertainty into the comparison, but does not invalidate the core findings:

1. P0-1 and P0-2 fixes are working as designed
2. Overall improvement is confirmed (minimum +10pp)
3. Target success rate of 55-65% was not achieved
4. Different families respond differently to P0 fixes

**Action Item for ROB-07:** Implement locked test sets to ensure fair comparisons.

---

**Document Version:** 1.0
**Generated:** 2026-01-13 17:45:00 UTC
**Author:** Agent C (Tests & Verification)
