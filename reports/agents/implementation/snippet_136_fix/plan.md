# Implementation Plan: Fix Context Inference for Using-Only Code

**Task**: T4
**Agent**: B (Implementation)
**Date**: 2026-01-12 14:25
**Status**: IN PROGRESS

---

## Problem Statement

**Snippet 136** contains only using statements with comments:
```csharp
using Aspose.Zip;                 // Archive, ArchiveEntry
using Aspose.Zip.Saving;          // DeflateCompressionSettings, CompressionLevel
```

**Current Behavior**:
- `_needs_context()` returns FALSE
- Code is sent to LLM without wrapper
- LLM adds executable code but cannot fix structural issue
- Compilation fails with CS0118, CS0210 errors

**Root Cause**: Line 420 in `src/persistent_fix_service.py`
```python
return not has_namespace and not has_class and (has_method or has_fields)
```

For using-only code:
- `has_namespace` = FALSE ✓
- `has_class` = FALSE ✓
- `has_method` = FALSE ✗ (no methods in using-only code)
- `has_fields` = FALSE ✗ (no fields in using-only code)
- Result: `not False and not False and (False or False)` = `True and True and False` = **FALSE**

**Expected**: Should return TRUE to trigger context wrapping

---

## Solution Design

### Approach: Add Using-Only Detection

Add a check for code that contains ONLY:
- Using statements
- Comments (// or /* */)
- Whitespace

**Implementation Location**: `src/persistent_fix_service.py`, line 419 (before return statement)

### Code Change

**Before** (lines 414-420):
```python
has_namespace = 'namespace ' in code
has_class = re.search(r'\b(class|interface|struct|enum)\s+\w+', code)
has_method = re.search(r'\w+\s+\w+\s*\([^)]*\)\s*{', code)
has_fields = re.search(r'(public|private|protected|internal)\s+\w+\s+\w+', code)

# Partial if: no namespace AND no class AND (has methods OR fields)
return not has_namespace and not has_class and (has_method or has_fields)
```

**After** (add lines between 418-419):
```python
has_namespace = 'namespace ' in code
has_class = re.search(r'\b(class|interface|struct|enum)\s+\w+', code)
has_method = re.search(r'\w+\s+\w+\s*\([^)]*\)\s*{', code)
has_fields = re.search(r'(public|private|protected|internal)\s+\w+\s+\w+', code)

# Check if code is ONLY using statements (with optional comments/whitespace)
has_using = 'using ' in code
if has_using and not has_namespace and not has_class:
    # Remove using statements, comments, and whitespace
    code_no_using = re.sub(r'using\s+[^;]+;', '', code)
    code_no_comments = re.sub(r'//.*?$|/\*.*?\*/', '', code_no_using, flags=re.MULTILINE | re.DOTALL)
    code_stripped = code_no_comments.strip()

    # If nothing left, code is using-only
    if not code_stripped:
        return True

# Partial if: no namespace AND no class AND (has methods OR fields)
return not has_namespace and not has_class and (has_method or has_fields)
```

### Logic Explanation

1. **Check for using statements**: `has_using = 'using ' in code`
2. **Ensure no existing structure**: `not has_namespace and not has_class`
3. **Strip all using statements**: `re.sub(r'using\s+[^;]+;', '', code)`
4. **Strip comments**: `re.sub(r'//.*?$|/\*.*?\*/', '', code_no_using, ...)`
5. **Check if anything remains**: If `code_stripped` is empty or only whitespace, return TRUE

**Result for Snippet 136**:
- `has_using` = TRUE
- `has_namespace` = FALSE
- `has_class` = FALSE
- After stripping using statements and comments: empty string
- Returns: **TRUE** ✓

---

## Expected Behavior After Fix

### Snippet 136 Processing Flow

**Step 1: Detection**
```python
_needs_context(code="using Aspose.Zip;\nusing Aspose.Zip.Saving;")
# Returns: TRUE (using-only code detected)
```

**Step 2: Context Inference**
```python
_infer_context(snippet_id=136, partial_code="using Aspose.Zip;\nusing Aspose.Zip.Saving;")
# Extracts: using statements, namespace, class from nearby snippets
# Returns: Complete wrapped code
```

**Step 3: Wrapped Code (Example)**
```csharp
using System;
using System.IO;
using Aspose.Zip;
using Aspose.Zip.Saving;

namespace AsposeDocs.Examples
{
    class ZipExamples
    {
        // Empty class body - valid C# code
    }
}
```

**Step 4: Compilation**
- Compiles successfully (empty class is valid)
- LLM receives valid code structure
- Can add methods/properties as needed

**Step 5: LLM Fix**
- LLM adds executable code inside class
- Code remains structurally valid
- Compilation succeeds

**Step 6: Extraction**
- `_extract_fixed_portion()` removes wrapper
- Returns only the original using statements (no changes needed)
- OR returns complete valid code if LLM added examples

---

## Edge Cases Handled

### Case 1: Using with Inline Comments
```csharp
using Aspose.Zip;  // Archive API
using Aspose.Zip.Saving;  // Compression settings
```
**Detection**: Strips comments → only using statements remain → Returns TRUE ✓

### Case 2: Using with Block Comments
```csharp
using Aspose.Zip;
/*
 * Additional namespaces for ZIP operations
 */
using Aspose.Zip.Saving;
```
**Detection**: Strips block comments → only using statements remain → Returns TRUE ✓

### Case 3: Using with Extra Whitespace
```csharp


using Aspose.Zip;

using Aspose.Zip.Saving;


```
**Detection**: `.strip()` removes whitespace → only using statements remain → Returns TRUE ✓

### Case 4: Using Plus Namespace (Not Using-Only)
```csharp
using System;

namespace MyApp { }
```
**Detection**: `has_namespace = TRUE` → condition fails early → Returns FALSE ✓
(Existing logic handles this correctly)

### Case 5: Using Plus Method (Not Using-Only)
```csharp
using System;

void DoWork() { }
```
**Detection**: `has_method = TRUE` → original logic returns TRUE ✓
(Existing logic handles this correctly)

---

## Testing Strategy

### Unit Test Cases (T6 will implement)

**Test 1: Using-Only Code**
```python
def test_needs_context_using_only():
    code = "using Aspose.Zip;\nusing Aspose.Zip.Saving;"
    result = service._needs_context(code)
    assert result == True, "Using-only code should need context"
```

**Test 2: Using with Comments**
```python
def test_needs_context_using_with_comments():
    code = "using Aspose.Zip;  // Archive API\nusing Aspose.Zip.Saving;  // Compression"
    result = service._needs_context(code)
    assert result == True, "Using with comments should need context"
```

**Test 3: Using Plus Namespace (Negative)**
```python
def test_needs_context_using_with_namespace():
    code = "using System;\n\nnamespace MyApp { }"
    result = service._needs_context(code)
    assert result == False, "Code with namespace should not need context"
```

**Test 4: Using Plus Method (Positive)**
```python
def test_needs_context_using_with_method():
    code = "using System;\n\nvoid DoWork() { }"
    result = service._needs_context(code)
    assert result == True, "Partial method code should need context"
```

**Test 5: Empty String (Negative)**
```python
def test_needs_context_empty():
    code = ""
    result = service._needs_context(code)
    assert result == False, "Empty code should not need context"
```

### Integration Test (T9 will execute)

**Snippet 136 Validation**:
1. Reset snippet status to 'unverified'
2. Run validation with persistent fix enabled
3. Verify snippet status changes to 'verified'
4. Check database: `context_inferred = TRUE` in `fixes_applied` table

---

## Rollback Strategy

### If Fix Causes Issues

**Symptoms of Problem**:
- Previously working snippets now fail
- Context inference triggers incorrectly
- Compilation errors increase

**Rollback Steps**:
1. Revert `src/persistent_fix_service.py` lines 419-428 (remove using-only check)
2. Original logic remains:
   ```python
   return not has_namespace and not has_class and (has_method or has_fields)
   ```
3. No database changes needed (context_inferred flag is optional)
4. Re-run validation to verify no regressions

**Git Command**:
```bash
git checkout HEAD -- src/persistent_fix_service.py
```

### Partial Rollback (If Only Using-Only Detection Fails)

If using-only detection has false positives:
```python
# More conservative check - require at least 1 using statement
if has_using and not has_namespace and not has_class and not has_method and not has_fields:
    # Check if ALL non-whitespace lines are using statements
    lines = [line.strip() for line in code.split('\n') if line.strip()]
    using_lines = [line for line in lines if line.startswith('using ')]
    comment_lines = [line for line in lines if line.startswith('//') or line.startswith('/*')]

    if len(using_lines) + len(comment_lines) == len(lines):
        return True
```

---

## Performance Impact

**Before Fix**:
- `_needs_context()` executes 4 regex searches
- Time: ~0.1ms per call

**After Fix**:
- Additional check: 3 regex substitutions (only when using detected)
- Time: ~0.2ms per call (2x slower)
- Frequency: Only for using-only code (~1% of snippets)
- Total impact: Negligible (<1ms per validation run)

---

## Security Considerations

**Regex Denial of Service (ReDoS) Risk**: LOW
- Pattern `r'using\s+[^;]+;'` is simple, no nested quantifiers
- Pattern `r'//.*?$|/\*.*?\*/'` uses non-greedy quantifier, minimal backtracking
- Input size: Limited to snippet code (typically <500 lines)

**Code Injection Risk**: NONE
- No code execution, only string manipulation
- No eval(), exec(), or dynamic imports

---

## Documentation Updates (T12 will implement)

Files to update:
1. **docs/validation.md**: Add section on context inference for using-only code
2. **docs/architecture.md**: Update persistent fix service documentation
3. **CHANGELOG.md**: Add entry for fix

---

## Acceptance Criteria

- [x] Fix design documented (THIS FILE)
- [ ] Code change implemented in `src/persistent_fix_service.py` (T5)
- [ ] Unit tests created and passing (T6)
- [ ] Snippet 136 status = 'verified' after validation (T9)
- [ ] No regressions in other snippets (T9)
- [ ] Documentation updated (T12)

---

## Risk Assessment

**Risk Level**: LOW

**Why Low Risk**:
1. Minimal code change (8 lines added)
2. Only affects using-only code (rare case)
3. Existing logic preserved (no modifications to original return statement)
4. Easy rollback (single file change)
5. Well-defined edge cases with test coverage

**Mitigation**:
- Comprehensive unit tests (T6)
- Integration testing with real snippets (T9)
- Regression checks on all previously verified snippets (T9)

---

**Agent B Conclusion**: Design complete. Ready to proceed to T5 (Implementation) and T6 (Unit Tests).
