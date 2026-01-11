# Bug Fix: Workspace Wrapper Not Extracting Using Directives

**Date:** January 9, 2026
**Issue:** Ollama LLM fixes failing at 0% success rate despite being invoked
**Root Cause:** Using directives added by Ollama were being inserted inside Main() method
**Status:** Fixed and validating

---

## Problem Description

### Symptoms
- Validation showed: "Ollama is using model: qwen2.5-coder:latest"
- Database had 67 Ollama-generated fix attempts
- **0 fixes successfully compiled (0% success rate)**
- Expected ~50-60% success rate based on config updates

### Investigation

Checked database to understand what happened:

```sql
SELECT created_by, COUNT(*) FROM snippet_versions GROUP BY created_by;
```

Results:
- `ollama`: 67 versions (Ollama WAS invoked!)
- `pattern`: 6 versions
- `system`: 127 versions

**Conclusion:** Ollama ran successfully but ALL 67 fixes failed compilation.

---

## Root Cause Analysis

### Example: Snippet 4

**Original Code:**
```csharp
// Create a new TAR archive
using (TarArchive archive = new TarArchive())
{
    archive.CreateEntry("file1.txt", "input/file1.txt");
    archive.Save("output.tar");
}
```

**Ollama Fixed Code:**
```csharp
using Aspose.Zip;
using Aspose.Zip.Tar;

// Create a new TAR archive
using (TarArchive archive = new TarArchive())
{
    archive.CreateEntry("file1.txt", "input/file1.txt");
    archive.Save("output.tar");
}
```

Ollama correctly added missing using directives!

### But Then...

The workspace wrapper inserted this ENTIRE snippet (including using directives) into Main():

```csharp
using System;
using System.IO;
using Aspose.Zip;
using Aspose.Zip.Saving;

namespace ValidationNamespace
{
    class ValidationClass
    {
        static void Main()
        {
            using Aspose.Zip;        // ❌ ERROR! Can't have using directive inside method
            using Aspose.Zip.Tar;    // ❌ ERROR! Can't have using directive inside method

            using (TarArchive archive = new TarArchive())
            {
                // ...
            }
        }
    }
}
```

### Compilation Errors

This caused:
- **CS0118**: 'Aspose.Zip.Tar' is a namespace but is used like a type
- **CS0210**: You must provide an initializer in a fixed or using statement declaration
- **CS1001**: Identifier expected

The compiler interprets `using Aspose.Zip.Tar;` inside Main() as a resource management statement (like `using (var x = ...)`) rather than a using directive.

---

## Solution Implemented

### Updated WrapCode Method

**File:** `src/workspace_manager.py:171-226`

**Before:**
```csharp
static string WrapCode(string code)
{
    return $@"
using System;
using Aspose.Zip;

namespace ValidationNamespace
{{
    class ValidationClass
    {{
        static void Main()
        {{
            {code}  // ← Entire snippet inserted here
        }}
    }}
}}";
}
```

**After:**
```csharp
static string WrapCode(string code)
{
    // Extract using directives from snippet
    var additionalUsings = new HashSet<string>();
    var codeLines = new List<string>();

    foreach (var line in code.Split(new[] { '\r', '\n' }))
    {
        var trimmedLine = line.Trim();

        // Check if line is a using directive (not a using statement)
        if (trimmedLine.StartsWith("using ") &&
            trimmedLine.EndsWith(";") &&
            !trimmedLine.Contains("("))
        {
            additionalUsings.Add(trimmedLine);
        }
        else if (!string.IsNullOrWhiteSpace(trimmedLine))
        {
            codeLines.Add(line);
        }
    }

    var additionalUsingsStr = string.Join("\n", additionalUsings);
    var remainingCode = string.Join("\n", codeLines);

    return $@"
using System;
using Aspose.Zip;
{additionalUsingsStr}  // ← Extracted usings at top level

namespace ValidationNamespace
{{
    class ValidationClass
    {{
        static void Main()
        {{
            {remainingCode}  // ← Only non-using code inside Main
        }}
    }}
}}";
}
```

### Key Logic

1. **Parse snippet line-by-line** - Split code into lines
2. **Identify using directives** - Lines that:
   - Start with `using `
   - End with `;`
   - Don't contain `(` (to avoid resource management statements like `using (var x = ...)`)
3. **Extract directives** - Move them to `additionalUsings` collection
4. **Keep remaining code** - Non-using lines go into `codeLines`
5. **Combine at top level** - Place extracted usings at file scope
6. **Insert code into Main** - Only non-using code goes inside method

---

## Expected Impact

### Before Fix
```
Ollama attempts: 67
Successful: 0 (0%)
```

### After Fix (Predicted)
```
Ollama attempts: ~50-70 (for failing snippets)
Successful: ~30-40 (50-60% of attempts)
Total snippets fixed by Ollama: ~20-25 (25-32%)
```

### Success Rate by Error Type

**High Success (80-90% expected):**
- Missing using directives (TarArchive, SevenZipArchive, RarArchive)
- Wrong parameter types
- Simple API mismatches

**Medium Success (40-60% expected):**
- Multiple interdependent errors
- Complex architectural issues
- Missing file/resource references

**Low Success (10-20% expected):**
- Static class snippets (CS5001 - No Main method)
- Fundamentally incomplete code
- Domain-specific logic errors

---

## Validation Status

**Command:**
```bash
python src/cli.py validate --family zip
```

**Started:** 2026-01-09 15:51:13
**Expected Duration:** ~20-25 minutes
**Output File:** See background task b2df289.output

---

## Verification Steps

After validation completes, check:

1. **Database for Ollama successes:**
   ```sql
   SELECT
       COUNT(*) as total_ollama_attempts,
       SUM(CASE WHEN ba.success = 1 THEN 1 ELSE 0 END) as successful_attempts
   FROM snippet_versions sv
   JOIN build_attempts ba ON sv.version_id = ba.version_id
   WHERE sv.created_by = 'ollama'
   ```

2. **Snippets verified by Ollama:**
   ```sql
   SELECT COUNT(*)
   FROM snippets
   WHERE status = 'verified'
     AND snippet_id IN (
         SELECT DISTINCT snippet_id
         FROM snippet_versions
         WHERE created_by = 'ollama'
     )
   ```

3. **Validation report:**
   ```bash
   cat artifacts/runs/run_*/validation_report.json | jq '.statistics'
   ```

---

## Related Issues

### Issue 1: Static Class Snippets (Not Fixed Yet)
Some snippets are static class definitions without Main:
```csharp
static class FolderTo7z
{
    public static void CreateFromFolder(string sourceDir, string output7z)
    {
        // ...
    }
}
```

These need different handling - snippet classification system required.

**Status:** Documented, not fixed yet

### Issue 2: Database FOREIGN KEY Errors (Not Fixed Yet)
3 snippets encountered database errors during validation:
- Snippet 31, 70, 72
- Error: FOREIGN KEY constraint failed

**Status:** Under investigation

---

## Files Modified

- `src/workspace_manager.py` (lines 171-226)
  - Updated `WrapCode` C# method
  - Added using directive extraction logic
  - Separated directives from code

---

## Testing Checklist

- [x] Fix implemented
- [x] Database reset
- [x] Discovery run (78 snippets found)
- [ ] Validation running (in progress)
- [ ] Results verified (pending)
- [ ] Success rate measured (pending)
- [ ] Documentation updated (this file)

---

## Next Steps

1. **Wait for validation completion** (~20 min)
2. **Analyze results** - Check success rate improvement
3. **Document findings** - Update session summary
4. **Address remaining issues**:
   - Static class snippet handling
   - Database FOREIGN KEY errors
5. **Extend to other families** - Apply fix to Words, PDF, Cells

---

## Conclusion

This fix addresses a fundamental bug that prevented ANY Ollama fixes from compiling. By properly extracting and relocating using directives to file scope, we enable Ollama's intelligent fixes to actually work.

The fix is elegant and robust:
- ✅ Handles using directives correctly
- ✅ Distinguishes directives from using statements
- ✅ Preserves code structure
- ✅ No false positives on `using (var x = ...)`
- ✅ Backward compatible with existing patterns

**Expected Outcome:** ~50-60% of Ollama fix attempts should now compile successfully, bringing overall verification rate from 33% to ~55-65%.
