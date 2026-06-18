# LLM Code Fixing Flow Documentation

**Purpose:** This document explains how the system uses local Ollama LLM to automatically fix compilation errors in code snippets.

---

## Overview

When a C# code snippet fails to compile, the system uses a local Ollama LLM (preferably a code-specialized model like `qwen2.5-coder`) to intelligently fix the errors while preserving the original intent and logic.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│         Validation Pipeline with LLM Integration          │
└──────────────────────────────────────────────────────────┘

[Code Snippet]
      │
      ▼
┌─────────────────────┐
│ 1. Initial Compile  │
│ (workspace_manager) │
└──────┬──────────────┘
       │
       ├─► Success? ──► Track verified candidate ──┐
       │                                           │
       ▼ Failed                                    │
┌─────────────────────┐                           │
│ 2. Pattern Fixes    │                           │
│ (pattern_registry)  │                           │
└──────┬──────────────┘                           │
       │                                           │
       ├─► Apply known patterns (SaveAsync → Save) │
       │                                           │
       ▼                                           │
┌─────────────────────┐                           │
│ 3. Compile Fixed    │                           │
└──────┬──────────────┘                           │
       │                                           │
       ├─► Success? ──► Track verified candidate ──┤
       │                                           │
       ▼ Still Failed                              │
┌─────────────────────┐                           │
│ 4. Ollama Fix Loop  │                           │
│ (10 iterations max) │                           │
└──────┬──────────────┘                           │
       │                                           │
       ├─► Iterative fixes with model fallback    │
       │    └─► Compile ──► Success? ──► Track candidate ──┤
       │                      │                    │
       │                      ▼ Failed             │
       └─► [Continue to runtime validation] ──────┤
                                                   │
                                                   ▼
       ┌─────────────────────────────────────────────┐
       │ 4.5 Runtime Validation (if enabled)         │
       │ - Execute verified candidate in subprocess  │
       │ - Capture stdout/stderr/exceptions          │
       │ - Store execution_results in database       │
       └──────┬──────────────────────────────────────┘
              │
              ├─► Runtime Disabled? ──► Skip to Stage 5 ──┐
              │                                          │
              ├─► Runtime Success? ──► Continue ─────────┤
              │                                          │
              ▼ Runtime Failed                           │
         ┌─────────────────┐                            │
         │ Strict Mode?    │                            │
         └──────┬──────────┘                            │
                │                                        │
                ├─► Yes: Downgrade to [Needs Fix] ⚠️    │
                │        No patching                     │
                │                                        │
                └─► No (Lenient): Keep verified + warning │
                                                         │
                                                         ▼
                                            ┌──────────────────────┐
                                            │ 4.6 Patching         │
                                            │ - Only if verified   │
                                            │ - Apply code to MD   │
                                            └──────────────────────┘
                                                         │
                                                         ▼
                                            ┌──────────────────────┐
                                            │ 5. Finalization      │
                                            │ - Save versions      │
                                            │ - Update metrics     │
                                            └──────────────────────┘
```

---

## What Gets Sent to the LLM

### Input Components

When requesting a fix from Ollama, the system sends:

```python
{
    "model": "qwen2.5-coder:latest",
    "prompt": "<constructed_prompt>",  # See below
    "stream": false,
    "options": {
        "temperature": 0.1,    # Low temp for consistency
        "top_p": 0.9,
        "max_tokens": 4096
    }
}
```

### Prompt Structure

The prompt is carefully constructed with the following sections:

#### 1. System Context
```
You are a C# code fixer for Aspose.ZIP for .NET library (NuGet: Aspose.ZIP).
```

#### 2. Task Definition (varies by attempt)
```
Attempt 1: "Fix ONLY the compilation errors listed below."

Attempt 2: "The previous fix attempt failed. Be more careful to use
           ONLY existing APIs. Fix ONLY the compilation errors."

Attempt 3: "This is the FINAL attempt. You MUST use ONLY the APIs that
           exist in the library. Do NOT hallucinate methods."
```

#### 3. Compilation Errors
```
**COMPILATION ERRORS:**
CS0103: The name 'SaveAsync' does not exist in the current context
CS0246: The type or namespace name 'DeflateOptions' could not be found
```

#### 4. Non-Existent API List (Critical!)
```
**CRITICAL: The following methods/APIs do NOT EXIST in this library:**
   - SaveAsync (use Save instead)
   - CreateZipAsync (use CreateZip instead)
   - DeflateOptions (use DeflateCompressionSettings instead)

**DO NOT use ANY of the above APIs. They will cause compilation errors.**
```

This list comes from `config/families/{family}.json` → `non_existent_apis`

#### 5. Common Imports
```
**Common imports for this library:**
   using System;
   using System.IO;
   using System.Collections.Generic;
   using Aspose.Zip;
   using Aspose.Zip.Saving;
```

#### 6. Code to Fix
```
**CODE TO FIX:**
\`\`\`csharp
using (Archive archive = new Archive())
{
    await archive.SaveAsync("output.zip");  // ❌ SaveAsync doesn't exist
}
\`\`\`
```

#### 7. Instructions
```
**INSTRUCTIONS:**
1. Fix ONLY the compilation errors listed above
2. Preserve the original logic and structure
3. Do NOT hallucinate methods from the NON-EXISTENT list
4. Do NOT add try-catch, logging, or error handling unless required
5. Do NOT add comments or explanations
6. Return ONLY the fixed code inside a single ```csharp code fence
```

#### 8. Request Fixed Code
```
**FIXED CODE:**
```

### Full Example Prompt

```
You are a C# code fixer for Aspose.ZIP for .NET library (NuGet: Aspose.ZIP).

**YOUR TASK:** Fix ONLY the compilation errors listed below.

**COMPILATION ERRORS:**
CS1061: 'Archive' does not contain a definition for 'SaveAsync'

**CRITICAL: The following methods/APIs do NOT EXIST in this library:**
   - SaveAsync (use Save instead)
   - CreateZipAsync (use CreateZip instead)
   - DeflateOptions (use DeflateCompressionSettings instead)

**DO NOT use ANY of the above APIs. They will cause compilation errors.**

**Common imports for this library:**
   using System;
   using System.IO;
   using Aspose.Zip;
   using Aspose.Zip.Saving;

**CODE TO FIX:**
\`\`\`csharp
using (Archive archive = new Archive())
{
    archive.CreateEntry("file.txt", "content.txt");
    await archive.SaveAsync("output.zip");
}
\`\`\`

**INSTRUCTIONS:**
1. Fix ONLY the compilation errors listed above
2. Preserve the original logic and structure
3. Do NOT hallucinate methods from the NON-EXISTENT list
4. Do NOT add try-catch, logging, or error handling unless required for compilation
5. Do NOT add comments or explanations
6. Return ONLY the fixed code inside a single ```csharp code fence

**FIXED CODE:**
```

---

## What the LLM Returns

### Expected Response Format

The LLM should return the fixed code in a code fence:

```csharp
using (Archive archive = new Archive())
{
    archive.CreateEntry("file.txt", "content.txt");
    archive.Save("output.zip");  // ✅ Fixed: SaveAsync → Save
}
```

### Response Parsing

The system uses regex to extract code from the response:

```python
patterns = [
    r'```(?:csharp|c#)\s*\n(.*?)\n```',  # Prefer csharp fence
    r'```\s*\n(.*?)\n```'                 # Fallback to any fence
]
```

Safety checks:
- Code length > 0
- Code length < 50,000 chars (prevent hallucination)

---

## Why This Approach Works

### 1. **Low Temperature (0.1)**
- Ensures consistent, conservative fixes
- Reduces hallucination and creativity
- Makes LLM focus on the specific error

### 2. **Explicit Non-Existent API List**
- Prevents LLM from inventing methods
- Common issue: LLMs "imagine" `SaveAsync` exists
- List acts as a hard constraint

### 3. **Progressive Strictness**
- Attempt 1: Polite request
- Attempt 2: More stern warning
- Attempt 3: FINAL warning with emphasis on hallucination
- Increases success rate on stubborn errors

### 4. **Minimal Instructions**
- "Fix ONLY the compilation errors"
- Prevents LLM from refactoring or improving code
- Keeps diff minimal for easier review

### 5. **Context from Family Config**
- `non_existent_apis`: Prevents common mistakes
- `common_usings`: Suggests likely missing imports
- `ollama_context`: Family-specific guidance

---

## Configuration: `config/families/zip.json`

### Key Sections for LLM

```json
{
  "family": "zip",
  "display_name": "Aspose.ZIP for .NET",

  "non_existent_apis": [
    "SaveAsync - Use Save instead",
    "CreateZipAsync - Use CreateZip instead",
    "DeflateOptions - Use DeflateCompressionSettings"
  ],

  "ollama_context": {
    "common_usings": [
      "using System;",
      "using System.IO;",
      "using System.Collections.Generic;",
      "using Aspose.Zip;",
      "using Aspose.Zip.Saving;"
    ],
    "common_patterns": [
      "Archives are created with: new Archive()",
      "Entries are added with: archive.CreateEntry(name, source)",
      "Archives are saved with: archive.Save(path)"
    ]
  }
}
```

### How to Identify Non-Existent APIs

1. **During validation:** Track APIs that cause CS0103/CS1061 errors repeatedly
2. **Manual review:** Check official Aspose.ZIP documentation
3. **Failure analysis:** Use automated pattern detection (see failure-pattern-analysis-plan.md)
4. **Add to config:** Update `non_existent_apis` list

---

## Success Metrics

### Compilation After LLM Fix

```
Attempt 1: ~40% success rate
Attempt 2: ~25% success rate (on attempt 1 failures)
Attempt 3: ~15% success rate (on attempt 2 failures)

Overall: ~60-70% of failures fixed by Ollama
Remaining: ~30-40% need manual intervention
```

### What LLM Fixes Well

✅ **Good at:**
- Replacing non-existent methods with correct ones
- Adding missing using statements
- Fixing parameter types
- Simple async/await issues
- Variable type corrections

❌ **Struggles with:**
- Complex architectural changes
- Missing file/resource references
- Logic errors (not syntax)
- Multiple interdependent errors
- Domain-specific knowledge gaps

---

## Ensuring Fixes Are Relevant

### Validation Strategy

After LLM returns fixed code, the system:

1. **Compiles the fixed code** using Roslyn
   - If it compiles: ✅ Accept
   - If it fails: ❌ Try next attempt (or fail)

2. **Stores both versions** in database:
   - Original code (version_type='original')
   - Fixed code (version_type='ollama_1', 'ollama_2', etc.)
   - Build attempts for each

3. **Manual review** (future):
   - Generate diff: `original.cs` → `fixed.cs`
   - Flag if changes > 30% of code (likely over-refactored)
   - Require human approval before patching

### Preventing Over-Refactoring

Current safeguards:
- Instruction: "Fix ONLY the compilation errors"
- Instruction: "Preserve the original logic and structure"
- Low temperature (0.1) prevents creativity

Future enhancements:
- Calculate code similarity score (Levenshtein distance)
- Reject if similarity < 70%
- AST-based diff analysis (structural vs formatting changes)

---

## Example Fix Scenarios

### Scenario 1: Non-Existent Method

**Original Code (fails):**
```csharp
using (Archive archive = new Archive())
{
    await archive.SaveAsync("output.zip");
}
```

**Error:**
```
CS1061: 'Archive' does not contain a definition for 'SaveAsync'
```

**LLM Fixed Code:**
```csharp
using (Archive archive = new Archive())
{
    archive.Save("output.zip");
}
```

**Result:** ✅ Compiles successfully

---

### Scenario 2: Wrong API Class

**Original Code (fails):**
```csharp
var options = new DeflateOptions
{
    CompressionLevel = 9
};
archive.Save("out.zip", options);
```

**Error:**
```
CS0246: The type or namespace name 'DeflateOptions' could not be found
```

**LLM Fixed Code:**
```csharp
var options = new DeflateCompressionSettings();
archive.Save("out.zip", new ArchiveSaveOptions { CompressionSettings = options });
```

**Result:** ✅ Compiles successfully

---

### Scenario 3: Missing Using Statement

**Original Code (fails):**
```csharp
List<string> files = new List<string>();
archive.CreateEntry("file.txt", "data.txt");
```

**Error:**
```
CS0246: The type or namespace name 'List<>' could not be found
```

**LLM Fixed Code:**
```csharp
using System.Collections.Generic;

List<string> files = new List<string>();
archive.CreateEntry("file.txt", "data.txt");
```

**Result:** ✅ Compiles successfully

---

## Troubleshooting

### Issue: LLM Keeps Hallucinating Methods

**Solution:**
1. Add problematic API to `non_existent_apis` in family config
2. Use attempt 3 (strongest warnings)
3. Consider switching to more conservative model

### Issue: LLM Over-Refactors Code

**Solution:**
1. Check if instructions are too vague
2. Lower temperature (already at 0.1)
3. Add manual review step before accepting

### Issue: LLM Fixes Break Logic

**Solution:**
1. Implement code similarity check
2. Add unit test execution for snippets
3. Manual review for low-similarity fixes

---

## Model Selection Priority

The system auto-selects the best available model:

1. **qwen2.5-coder** (Preferred) - Excellent C# support, low hallucination
2. **deepseek-coder** (Good) - Strong code understanding
3. **codellama** (Okay) - Decent but less accurate
4. **llama3.1** (Fallback) - General purpose, not code-specialized
5. **mistral** (Last resort) - Can work but less reliable

**Recommendation:** Pull qwen2.5-coder before running:
```bash
ollama pull qwen2.5-coder
```

---

## Performance Considerations

### Time per Snippet

- **Pattern fixes:** ~0.1 seconds
- **Ollama attempt 1:** ~5-15 seconds (depends on model and code size)
- **Ollama attempt 2:** ~5-15 seconds
- **Ollama attempt 3:** ~5-15 seconds

**Total:** Up to 45 seconds per failing snippet (if all attempts needed)

For 78 snippets with 50% failure rate:
- 39 failures × 3 attempts × 10 sec avg = **~20 minutes**

### Optimization Strategies

1. **Batch processing:** Process multiple snippets in parallel (not yet implemented)
2. **Early termination:** Stop after attempt 1 success (already done)
3. **Model caching:** Keep Ollama warm (already persistent)
4. **Smaller models:** Use `qwen2.5-coder:3b` instead of `:7b` for speed

---

## Future Enhancements

### 1. Learning from Fixes
- Store (error, fix) pairs in database
- Build custom fine-tuning dataset
- Train family-specific model

### 2. Confidence Scoring
- Calculate confidence for each fix
- Auto-accept high confidence (>0.9)
- Flag low confidence for review (<0.5)

### 3. Multi-Model Consensus
- Ask 2-3 models for fixes
- Compare results
- Accept if 2+ agree

### 4. Interactive Mode
- Show user the proposed fix
- Ask for approval before compiling
- Learn from user feedback

---

## Related Documentation

- [Architecture](architecture.md)
- [Patching Strategies](patching-strategies.md)
- [LLM Service](../../src/services/llm_service.py)
- [Pipeline Orchestrator](../../src/pipeline/orchestrator.py)

---

## Conclusion

The LLM-based code fixing system provides an intelligent, automated way to resolve compilation errors while maintaining code relevance and quality. By carefully crafting prompts with domain-specific context and constraints, we achieve a 60-70% success rate on automatic fixes, significantly reducing manual intervention.

**Key Takeaways:**
1. ✅ Low temperature + explicit constraints = consistent, safe fixes
2. ✅ Non-existent API list prevents hallucination
3. ✅ Progressive strictness improves stubborn errors
4. ✅ Validation via compilation ensures relevance
5. ✅ Always preserve original code for comparison
