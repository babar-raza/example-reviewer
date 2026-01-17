# ROB-04 Quick Reference Card

## One-Liner Summary
**97.1% of failures are false positive infinite loop detections** - loop threshold too aggressive at 3 iterations.

## Top 3 Fixes (in priority order)

### 1. P0-1: Increase Loop Detection Threshold
```python
# Change from 3 to 6-8 iterations before declaring infinite loop
# Expected impact: +30-40% success rate (unlock 25-35 snippets)
```

### 2. P0-2: Fix PDF Diagnostics
```python
# PDF validator returns "Validator build failed:" with no details
# Expected impact: +10-15% success rate (unlock PDF family)
```

### 3. P1-1: Expand Assembly References
```python
# Cells: Add missing Aspose.Cells packages
# Imaging: Add missing assembly references
# Expected impact: +10-15% success rate
```

## Key Numbers
- **Total failures**: 69/90 (76.7%)
- **Infinite loop false positives**: 67 (97.1% of failures)
- **PDF family**: 0/15 success, all stopped at exactly 3 iterations
- **Top error**: CS0246 (1322 occurrences) - type/namespace not found

## Error Code Cheat Sheet
| Code | Meaning | Count | Fix Strategy |
|------|---------|-------|--------------|
| CS0246 | Type not found | 1322 | Add using directive |
| CS0012 | Unreferenced assembly | 930 | Add package reference |
| CS0103 | Name doesn't exist | 345 | Check namespace/scope |
| CS1061 | Member not found | 85 | Check API version |

## Family Success Rates
```
Words:   66.7% ████████████████████████░░░░░░░░░
Slides:  60.0% ██████████████████████░░░░░░░░░░░
Email:    6.7% ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Imaging:  6.7% ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
PDF:      0.0% ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Cells:    0.0% ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

## Typical Iteration Patterns
- **PDF**: Always 3 iterations (premature termination)
- **Words/Slides**: 4-5 iterations (some progress)
- **Cells/Email/Imaging**: 5-7 iterations (stuck on assembly issues)

## Implementation Order
1. **Quick win** (1 hour): Change loop threshold in persistent_fix_service.py
2. **Moderate** (4 hours): Debug PDF validator diagnostic capture
3. **Research** (8 hours): Audit and expand family NuGet configs

## Expected Outcome
- **Before fixes**: 23.3% success
- **After P0 fixes**: 55-65% success
- **After P1 fixes**: 70-80% success
- **Target**: 65-75% minimum for ROB-05

## Files to Modify
1. `src/persistent_fix_service.py` - Loop detection threshold
2. `src/validation_orchestrator.py` - PDF diagnostic capture
3. `config/families/cells.json` - NuGet packages
4. `config/families/imaging.json` - Assembly references

## Next Run
- **ROB-05**: Re-run validation with P0 fixes applied
- **Focus**: PDF, Cells, Imaging families (currently 0-7% success)
- **Target**: Achieve 50-65% success rate minimum
