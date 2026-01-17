# User Guide: Example Reviewer Robustness Features

**Version**: 1.0
**Date**: 2026-01-13
**Author**: Agent D (Documentation & Quality)
**For**: Developers using the example-reviewer validation system

---

## Table of Contents

1. [Overview](#overview)
2. [Namespace Validator](#namespace-validator)
3. [Pattern Detector](#pattern-detector)
4. [Validation Workflow](#validation-workflow)
5. [Configuration Guide](#configuration-guide)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Overview

The example-reviewer system validates code snippets from Aspose product documentation by compiling them and applying automated fixes when compilation fails. The ROB-01 through ROB-08 initiative added two major capabilities:

1. **Namespace Validator**: Enforces namespace policies to prevent cross-domain API usage
2. **Pattern Detector**: Intelligently detects code patterns for better context inference

This guide explains how to use these features effectively.

---

## Namespace Validator

### What It Does

The namespace validator checks code snippets against family-specific namespace policies BEFORE compilation. This prevents:
- Cross-domain API usage (e.g., Words snippets using Aspose.PDF APIs)
- Unwanted dependencies (e.g., cloud services, web frameworks)
- Security risks (e.g., file system access, network operations)

### How It Works

**Stage 0 Validation** (before pattern fixes and compilation):

1. Extract all `using` directives from code
2. Check each namespace against family policy (whitelist/blacklist/permissive)
3. If violation found:
   - Mark snippet as `needs-fix`
   - Log violation to event_log
   - Increment telemetry metric
   - Early exit (no compilation attempt)

### Configuration

Each family configuration (`config/families/{family}.json`) includes a `namespace_policy` section:

```json
{
  "namespace_policy": {
    "mode": "whitelist",
    "allowed_namespaces": [
      "Aspose.Words",
      "Aspose.Words.*",
      "System",
      "System.IO",
      "System.Text",
      "System.Collections.Generic",
      "System.Linq"
    ],
    "blacklist": []
  }
}
```

### Policy Modes

#### 1. Whitelist Mode (Recommended)

**Use Case**: Restrict to specific namespaces only

**Configuration**:
```json
{
  "mode": "whitelist",
  "allowed_namespaces": [
    "Aspose.Words",
    "Aspose.Words.*",
    "System",
    "System.*"
  ]
}
```

**Behavior**:
- Only listed namespaces are allowed
- Wildcards supported (e.g., `Aspose.Words.*` allows `Aspose.Words.Drawing`, `Aspose.Words.Fields`, etc.)
- Any namespace NOT in list is rejected

**Example Violations**:
```csharp
using Aspose.Pdf;  // VIOLATION: Aspose.Pdf not in whitelist
using System.Net.Http;  // VIOLATION: System.Net.Http not in whitelist
```

#### 2. Blacklist Mode

**Use Case**: Allow most namespaces, block specific ones

**Configuration**:
```json
{
  "mode": "blacklist",
  "allowed_namespaces": [
    "Aspose.Words",
    "Aspose.Words.*",
    "System",
    "System.*"
  ],
  "blacklist": [
    "System.Net.Http",
    "System.Data.SqlClient",
    "Azure.*"
  ]
}
```

**Behavior**:
- All `allowed_namespaces` are permitted
- All `blacklist` namespaces are rejected (even if in allowed list)
- Wildcards supported in blacklist

**Example Violations**:
```csharp
using System.Net.Http;  // VIOLATION: In blacklist
using Azure.Storage.Blobs;  // VIOLATION: Matches Azure.* blacklist pattern
```

#### 3. Permissive Mode

**Use Case**: Allow all namespaces (no restrictions)

**Configuration**:
```json
{
  "mode": "permissive"
}
```

**Behavior**:
- All namespaces allowed
- No validation performed
- Use for testing or when no restrictions needed

### Wildcard Patterns

**Exact Match**:
```json
"allowed_namespaces": ["Aspose.Words"]
```
- Allows: `using Aspose.Words;`
- Rejects: `using Aspose.Words.Drawing;`

**Wildcard Match**:
```json
"allowed_namespaces": ["Aspose.Words.*"]
```
- Allows: `using Aspose.Words;` (exact match)
- Allows: `using Aspose.Words.Drawing;` (sub-namespace)
- Allows: `using Aspose.Words.Drawing.Charts;` (deep sub-namespace)
- Rejects: `using Aspose.Pdf;` (different namespace)

**System Wildcard** (common pattern):
```json
"allowed_namespaces": ["System", "System.*"]
```
- Allows all `System.*` namespaces (IO, Text, Collections, Linq, Net, Data, etc.)
- Shorthand for comprehensive System namespace access

### Checking Namespace Violations

**Query event log**:
```sql
SELECT snippet_id, event_details
FROM event_log
WHERE event_type = 'namespace_violation'
  AND run_id = (SELECT MAX(run_id) FROM runs)
ORDER BY created_at DESC;
```

**Query telemetry**:
```python
from telemetry import TelemetryClient
client = TelemetryClient()
violations = client.get_metric('namespace_violations')
print(f"Total violations: {violations}")
```

**Example Output**:
```
Snippet 454 (PDF): Namespace not allowed: System.Net.Http; System.Net.Http.Headers; Newtonsoft.Json
Snippet 455 (PDF): Namespace not allowed: System.Data
```

### Adding Allowed Namespaces

**Step 1**: Identify needed namespace from violation log

**Step 2**: Edit family configuration
```bash
# Open family config
notepad config\families\pdf.json

# Add namespace to allowed_namespaces array
"allowed_namespaces": [
  "Aspose.Pdf",
  "Aspose.Pdf.*",
  "System",
  "System.*",
  "System.Net.Http",      # ← ADD THIS
  "System.Net.Http.*"     # ← ADD THIS
]
```

**Step 3**: Validate JSON syntax
```bash
python -m json.tool config\families\pdf.json
# If no output, syntax is valid
```

**Step 4**: Re-run validation
```bash
python src\cli.py validate --family pdf --max-snippets 15
```

---

## Pattern Detector

### What It Does

The pattern detector analyzes code snippets to determine their structure and automatically selects the appropriate context wrapping strategy. This prevents unnecessary class/namespace wrappers for self-contained code (e.g., C# 9+ top-level statements).

### Pattern Types

| Pattern | Description | Confidence | Needs Wrapping? |
|---------|-------------|------------|-----------------|
| COMPLETE_PROGRAM | Full `class Program { static void Main() }` | 0.95 | No |
| TOP_LEVEL_STATEMENTS | C# 9+ executable statements outside class | 0.85 | No |
| MINIMAL_API | ASP.NET Core 6+ minimal API | 0.90 | No |
| CLASS_ONLY | Complete class definitions, no loose code | 0.80 | No |
| METHOD_ONLY | Standalone methods, no class | 0.75 | Yes (wrap in class) |
| FRAGMENT | Incomplete code snippets | 0.60 | Yes (wrap in class + namespace) |

### How It Works

**Detection Process**:

1. Strip comments from code
2. Check for COMPLETE_PROGRAM pattern (`class Program` + `Main` method)
3. Check for MINIMAL_API pattern (`WebApplication.CreateBuilder` + `app.Run()`)
4. Check for CLASS_ONLY pattern (has class definition, no loose code)
5. Check for METHOD_ONLY pattern (has method definition, no class)
6. Check for TOP_LEVEL_STATEMENTS pattern (executable statements outside class)
7. Default to FRAGMENT if no other pattern matches

**Context Inference**:
```python
# In PersistentFixService._needs_context()
pattern, confidence = self.pattern_detector.detect(code)

if pattern in [CodePattern.METHOD_ONLY, CodePattern.FRAGMENT]:
    return True  # Needs wrapping
else:
    return False  # Self-contained, no wrapping
```

### Examples

#### COMPLETE_PROGRAM (No Wrapping)

**Input**:
```csharp
using Aspose.Words;

class Program
{
    static void Main()
    {
        Document doc = new Document("input.docx");
        doc.Save("output.pdf");
    }
}
```

**Detection**: COMPLETE_PROGRAM (0.95 confidence)
**Action**: No wrapping, compile as-is

---

#### TOP_LEVEL_STATEMENTS (No Wrapping)

**Input**:
```csharp
using Aspose.Words;

Document doc = new Document("input.docx");
doc.Save("output.pdf");
```

**Detection**: TOP_LEVEL_STATEMENTS (0.85 confidence)
**Action**: No wrapping (C# 9+ feature, compiles as-is)

---

#### CLASS_ONLY (No Wrapping)

**Input**:
```csharp
using Aspose.Words;

public class DocumentHelper
{
    public void ConvertToPdf(string input, string output)
    {
        Document doc = new Document(input);
        doc.Save(output);
    }
}
```

**Detection**: CLASS_ONLY (0.80 confidence)
**Action**: No wrapping (complete class definition)

---

#### METHOD_ONLY (Wrap in Class)

**Input**:
```csharp
public void ConvertToPdf(string input, string output)
{
    Document doc = new Document(input);
    doc.Save(output);
}
```

**Detection**: METHOD_ONLY (0.75 confidence)
**Action**: Wrap in class
```csharp
using Aspose.Words;

class Program
{
    public void ConvertToPdf(string input, string output)
    {
        Document doc = new Document(input);
        doc.Save(output);
    }

    static void Main() { }
}
```

---

#### FRAGMENT (Wrap in Class + Namespace)

**Input**:
```csharp
Document doc = new Document("input.docx");
doc.Save("output.pdf");
```

**Detection**: FRAGMENT (0.60 confidence)
**Action**: Wrap in class + namespace + add using directives
```csharp
using Aspose.Words;

namespace Validator
{
    class Program
    {
        static void Main()
        {
            Document doc = new Document("input.docx");
            doc.Save("output.pdf");
        }
    }
}
```

### Checking Pattern Distribution

**Query telemetry**:
```python
from telemetry import TelemetryClient
client = TelemetryClient()

for pattern in ['complete_program', 'top_level_statements', 'minimal_api',
                'class_only', 'method_only', 'fragment']:
    count = client.get_metric(f'pattern_detected_{pattern}')
    print(f"{pattern}: {count}")
```

**Example Output**:
```
complete_program: 12
top_level_statements: 5
minimal_api: 0
class_only: 23
method_only: 18
fragment: 26
```

---

## Validation Workflow

### Step 1: Discover Content

**Command**:
```bash
python src\cli.py discover --family words \
  --content-root "D:\onedrive\Documents\GitHub\aspose.net"
```

**Output**:
```
Discovered 41 KB pages for family 'words'
Total snippets: 229
Database updated: 41 pages, 229 snippets
```

### Step 2: Build API Index (Optional)

**Command**:
```bash
python src\cli.py build-api-index --family words \
  --reference-root "D:\onedrive\Documents\GitHub\aspose.net\content\reference.aspose.net"
```

**Output**:
```
API Indexing Results for 'words':
- Classes indexed: 140
- Members indexed: 923
- Files skipped: 21
```

### Step 3: Validate Snippets

**Command**:
```bash
python src\cli.py validate --family words --max-snippets 15
```

**Output**:
```
Validation Progress:
[✓] Snippet 201 verified (1/15)
[✗] Snippet 203 failed: Namespace policy violation: System.Net.Http (2/15)
[✓] Snippet 205 verified (3/15)
...
Results: 11/15 verified (73.3%)
```

### Step 4: Review Results

**Query database**:
```sql
-- Success rate by family
SELECT p.family,
       COUNT(DISTINCT ba.snippet_id) as total,
       SUM(CASE WHEN ba.success = 1 THEN 1 ELSE 0 END) as success,
       ROUND(100.0 * SUM(CASE WHEN ba.success = 1 THEN 1 ELSE 0 END) / COUNT(DISTINCT ba.snippet_id), 1) as rate
FROM build_attempts ba
JOIN snippets s ON ba.snippet_id = s.snippet_id
JOIN pages p ON s.page_id = p.page_id
WHERE ba.run_id = (SELECT MAX(run_id) FROM runs)
GROUP BY p.family
ORDER BY rate DESC;
```

**Output**:
```
family  | total | success | rate
--------|-------|---------|------
words   | 15    | 11      | 73.3
slides  | 13    | 9       | 69.2
cells   | 15    | 10      | 66.7
imaging | 15    | 2       | 13.3
email   | 11    | 1       | 9.1
pdf     | 15    | 0       | 0.0
```

---

## Configuration Guide

### Family Configuration Template

**File**: `config/families/{family}.json`

```json
{
  "family": "words",
  "display_name": "Aspose.Words for .NET",
  "auto_commit": false,
  "commit_message_template": "fix: [words] Patch {patch_count} snippet(s) {snippet_ids}",

  "content_pattern": {
    "blog": "**/{family}/*/index.md",
    "docs": "**/{family}/en/**/*.md",
    "kb": "**/{family}/en/**/*.md",
    "products": "**/{family}/en/**/*.md",
    "reference": "**/{family}/en/**/*.md"
  },

  "nuget_config": {
    "primary_package": {
      "name": "Aspose.Words",
      "version": "*"
    },
    "additional_packages": [],
    "target_frameworks": ["net8.0"]
  },

  "code_defaults": {
    "default_usings": [
      "Aspose.Words",
      "Aspose.Words.Drawing",
      "Aspose.Words.Fields",
      "Aspose.Words.Tables",
      "Aspose.Words.Saving"
    ]
  },

  "namespace_policy": {
    "mode": "whitelist",
    "allowed_namespaces": [
      "Aspose.Words",
      "Aspose.Words.*",
      "System",
      "System.*"
    ],
    "blacklist": []
  },

  "persistent_fix": {
    "enabled": true,
    "max_iterations": 10,
    "iterations_per_model": 3,
    "max_time_seconds": 300,
    "enable_immediate_patching": true,
    "enable_context_inference": true
  }
}
```

### Global Configuration

**File**: `config/global.json`

```json
{
  "api_reference_paths": {
    "primary": "D:\\onedrive\\Documents\\GitHub\\aspose.net\\content\\references.aspose.net",
    "fallback": null
  },

  "api_index": {
    "auto_rebuild_on_validation": false,
    "cache_size": 128,
    "max_context_tokens": 2000,
    "default_max_classes": 5
  },

  "path_discovery": {
    "common_locations": [
      "D:\\onedrive\\Documents\\GitHub\\aspose.net\\content\\references.aspose.net"
    ]
  }
}
```

### Configuration Parameters

#### namespace_policy

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `mode` | string | Policy mode: "whitelist", "blacklist", "permissive" | "whitelist" |
| `allowed_namespaces` | array | Namespaces to allow (supports wildcards) | ["System", "System.*"] |
| `blacklist` | array | Namespaces to block (only in blacklist mode) | ["Azure.*"] |

#### persistent_fix

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `enabled` | boolean | Enable persistent fix service | true |
| `max_iterations` | integer | Maximum fix iterations per snippet | 10 |
| `iterations_per_model` | integer | Iterations before switching LLM model | 3 |
| `max_time_seconds` | integer | Maximum time per snippet (seconds) | 300 |
| `enable_immediate_patching` | boolean | Auto-patch verified snippets | true |
| `enable_context_inference` | boolean | Use pattern detector for context wrapping | true |

---

## Troubleshooting

### Issue 1: Namespace Policy Violations

**Symptom**:
```
[✗] Snippet 454 failed: Namespace policy violation: System.Net.Http
```

**Cause**: Snippet uses namespace not in family's whitelist

**Solution**:
1. Review snippet to determine if namespace is legitimate
2. If legitimate: Add to `allowed_namespaces` in family config
3. If not legitimate: Snippet may be out-of-scope (e.g., web app example)

**Example Fix**:
```json
// config/families/pdf.json
"allowed_namespaces": [
  "Aspose.Pdf",
  "Aspose.Pdf.*",
  "System",
  "System.*",
  "System.Net.Http",    // ← ADD THIS
  "System.Net.Http.*"   // ← ADD THIS
]
```

---

### Issue 2: Pattern Detector Incorrect Wrapping

**Symptom**:
```
[✗] Snippet 203 failed: CS1022: Type or namespace definition, or end-of-file expected
```

**Cause**: Pattern detector incorrectly classified code (e.g., TOP_LEVEL_STATEMENTS → FRAGMENT)

**Diagnosis**:
```python
from code_pattern_detector import CodePatternDetector
detector = CodePatternDetector()

# Test pattern detection
code = """..."""  # Paste failing snippet
pattern, confidence = detector.detect(code)
print(f"Detected: {pattern.value} (confidence: {confidence})")
```

**Solution**:
1. If confidence is low (<0.70): Pattern detection is uncertain
2. Check for edge cases:
   - Single-line variable declarations (should be FRAGMENT, not TOP_LEVEL_STATEMENTS)
   - Comments confusing detector (should strip comments first)
   - Namespace-wrapped classes (should detect CLASS_ONLY, not FRAGMENT)
3. Report false classifications as bug

---

### Issue 3: Iteration Limit Reached

**Symptom**:
```
[✗] Snippet 801 failed: Could not verify after all attempts (10 iterations)
```

**Cause**: Snippet requires >10 fix iterations (complex errors)

**Diagnosis**:
```sql
-- Check iteration count for snippet
SELECT ba.snippet_id, COUNT(*) as iterations,
       ba.error_count, ba.compiler_output
FROM build_attempts ba
WHERE ba.snippet_id = 801
GROUP BY ba.snippet_id
ORDER BY ba.attempt_id;
```

**Solution**:
1. Review error progression (error count should decrease over iterations)
2. If error count stuck (e.g., "5,5,5,5"): Infinite loop detected (expected behavior)
3. If error count decreasing (e.g., "10,7,5,3,2"): Increase `max_iterations` in family config
4. If error count oscillating (e.g., "5,3,5,3"): LLM trying different fix strategies (may need more iterations)

**Example Fix**:
```json
// config/families/cells.json
"persistent_fix": {
  "max_iterations": 15,  // ← Increase from 10
  ...
}
```

---

### Issue 4: Diagnostic Capture Empty

**Symptom**:
```
[✗] Snippet 437 failed: Validator build failed:
```

**Cause**: Validator returning empty compiler output (P0-2 fix should have resolved this)

**Diagnosis**:
```sql
-- Check compiler output length
SELECT snippet_id, LENGTH(compiler_output) as output_len,
       SUBSTR(compiler_output, 1, 100) as output_sample
FROM build_attempts
WHERE snippet_id = 437 AND success = 0
ORDER BY attempt_id DESC
LIMIT 5;
```

**Solution**:
1. If output_len < 30: Diagnostic capture failed
2. Check validator binary is working:
   ```bash
   # Test validator manually
   cd workspaces\{family}\validator
   dotnet build
   ```
3. If validator build succeeds manually: Issue with subprocess call in workspace_manager.py
4. If validator build fails manually: Issue with NuGet packages or project file

---

### Issue 5: NuGet Restore Timeout

**Symptom**:
```
[✗] Multiple snippets failed: CS0246: Type or namespace name not found
```

**Cause**: NuGet packages not restored (timeout during restore)

**Diagnosis**:
```bash
# Check if NuGet packages directory exists
dir workspaces\{family}\nuget-packages
# Should contain .nupkg files
```

**Solution**:
1. If directory empty: NuGet restore timed out
2. Increase timeout in workspace_manager.py:
   ```python
   # Line 450
   result = subprocess.run(
       cmd,
       capture_output=True,
       text=True,
       timeout=60  # ← Increase from 30
   )
   ```
3. Or manually restore packages:
   ```bash
   cd workspaces\{family}\validator
   dotnet restore
   ```

---

## Best Practices

### 1. Start with Permissive Mode

When creating a new family configuration:

1. Set `namespace_policy.mode` to `"permissive"` initially
2. Run validation to establish baseline
3. Review namespace usage in successful snippets
4. Switch to `"whitelist"` mode with commonly-used namespaces
5. Iterate based on violations

**Example**:
```json
// Initial config (permissive)
"namespace_policy": {
  "mode": "permissive"
}

// After baseline validation (whitelist)
"namespace_policy": {
  "mode": "whitelist",
  "allowed_namespaces": [
    "Aspose.{Family}",
    "Aspose.{Family}.*",
    "System",
    "System.IO",
    "System.Text",
    "System.Collections.Generic",
    "System.Linq"
  ]
}
```

---

### 2. Use System.* Wildcard for Simplicity

Instead of listing every System namespace individually:

**Don't**:
```json
"allowed_namespaces": [
  "System",
  "System.IO",
  "System.Text",
  "System.Collections.Generic",
  "System.Linq",
  "System.Threading.Tasks",
  "System.Net.Http",
  "System.Data",
  ...  // Many more
]
```

**Do**:
```json
"allowed_namespaces": [
  "System",
  "System.*"  // Allows ALL System namespaces
]
```

**Exception**: If you want to block specific System namespaces, use blacklist mode:
```json
"namespace_policy": {
  "mode": "blacklist",
  "allowed_namespaces": ["System", "System.*"],
  "blacklist": ["System.Net.Http", "System.Data.SqlClient"]
}
```

---

### 3. Monitor Telemetry for Pattern Distribution

Track which pattern types are common in your family:

```python
from telemetry import TelemetryClient
client = TelemetryClient()

patterns = {}
for pattern in ['complete_program', 'top_level_statements', 'minimal_api',
                'class_only', 'method_only', 'fragment']:
    patterns[pattern] = client.get_metric(f'pattern_detected_{pattern}')

# Analyze distribution
total = sum(patterns.values())
for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
    pct = 100 * count / total if total > 0 else 0
    print(f"{pattern}: {count} ({pct:.1f}%)")
```

**Use Insights**:
- If FRAGMENT is dominant (>50%): Snippets are incomplete, may need better context inference
- If TOP_LEVEL_STATEMENTS is common (>20%): Examples use modern C# features
- If METHOD_ONLY is common (>30%): Examples focus on individual methods, may need wrapping

---

### 4. Validate in Stages

Instead of validating all 90 snippets at once:

**Stage 1**: Validate 5-10 snippets per family
```bash
python src\cli.py validate --family words --max-snippets 5
```

**Stage 2**: Review failures, adjust namespace policies
```bash
notepad config\families\words.json
```

**Stage 3**: Validate next 10 snippets
```bash
python src\cli.py validate --family words --max-snippets 10
```

**Stage 4**: Repeat until policies stabilized

**Stage 5**: Full validation (15+ snippets)
```bash
python src\cli.py validate --family words --max-snippets 15
```

**Benefit**: Faster iteration cycles, easier to isolate issues

---

### 5. Document Policy Decisions

Add comments to family configurations explaining namespace policy decisions:

```json
{
  "namespace_policy": {
    "mode": "whitelist",
    "allowed_namespaces": [
      "Aspose.Words",
      "Aspose.Words.*",
      "System",
      "System.*",

      // Allow HTTP client for examples showing web integration
      "System.Net.Http",
      "System.Net.Http.*",

      // Allow JSON serialization for modern examples
      "Newtonsoft.Json",
      "Newtonsoft.Json.*",

      // Allow DataTable/DataSet for database integration examples
      "System.Data",
      "System.Data.*"
    ]
  }
}
```

**Note**: JSON doesn't support comments, so use a separate `POLICY_DECISIONS.md` file:
```markdown
# Words Family Namespace Policy Decisions

## Allowed Namespaces

### System.Net.Http
**Reason**: Many examples show document generation from web APIs
**Examples**: Snippets 203, 205, 207 (REST API integration)
**Date Added**: 2026-01-13

### Newtonsoft.Json
**Reason**: JSON serialization is common in modern C# examples
**Examples**: Snippets 209, 211 (JSON to Word conversion)
**Date Added**: 2026-01-13
```

---

## Conclusion

The namespace validator and pattern detector provide powerful capabilities for enforcing policies and improving validation success rates. Key takeaways:

1. **Start permissive, then restrict**: Use permissive mode to establish baseline, then switch to whitelist
2. **Use System.* wildcard**: Simplifies configuration, allows comprehensive System namespace access
3. **Monitor telemetry**: Track pattern distribution to optimize fix strategies
4. **Document decisions**: Explain namespace policy choices for future maintainers
5. **Validate incrementally**: Test 5-10 snippets at a time to iterate faster

For questions or issues, consult the technical report (`TECHNICAL_REPORT.md`) or lessons learned (`LESSONS_LEARNED.md`).

---

**Document Version**: 1.0
**Last Updated**: 2026-01-13
**Author**: Agent D (Documentation & Quality)
**Contact**: See project README for support channels
