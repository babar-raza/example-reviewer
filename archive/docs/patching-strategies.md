# Patching Strategies

## Overview

The Example Reviewer system supports two types of code snippets:
1. **Fenced Code Blocks** (inline in markdown)
2. **GitHub Gists** (Hugo shortcode references)

Each type has different patching strategies.

---

## Fence Patching (Standard)

**Behavior**: Replace code within existing fence markers.

**Strategy:**
```
Original:
    ```csharp
    class Old { }
    ```

After Patching:
    ```csharp
    class New { }
    ```
```

**Rules:**
- Fence markers (` ``` `) preserved
- Language marker preserved
- Only code content replaced
- Line endings preserved (CRLF/LF)

---

## Gist Patching (Phase 1)

**Key Principle**: Only replace gist shortcodes when code has changed.

### Patching Modes

#### 1. `inline-on-change` (Default)
Replace gist shortcode with inline fence **only if code changed**.

**Unchanged Gist:**
```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (code unchanged):
    {{< gist "aspose" "abc123" "Example.cs" >}}
    (No modification - shortcode preserved)
```

**Changed Gist:**
```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (code fixed):
    ```csharp
    class Example {
        // Fixed code here
    }
    ```
```

**Use Case:**
- Default mode for most workflows
- Preserves gist references when code is already correct
- Inlines only when fixes were applied

#### 2. `preserve`
Never replace gist shortcodes (always keep references).

```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (regardless of changes):
    {{< gist "aspose" "abc123" "Example.cs" >}}
    (Always preserved)
```

**Use Case:**
- When gists should remain as external references
- When you want validation without modification
- Preview mode to check what would change

**CLI:**
```bash
python src/cli.py patch --family zip --gist-mode preserve
```

#### 3. `inline-always`
Always replace gist shortcodes with inline fences (even if unchanged).

```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (always inlined):
    ```csharp
    class Example {
        // Code here (unchanged or fixed)
    }
    ```
```

**Use Case:**
- Migrating from gists to inline code
- Consolidating external references
- Ensuring all code is self-contained in markdown

**CLI:**
```bash
python src/cli.py patch --family zip --gist-mode inline-always
```

#### 4. `upload-on-change` (Phase 5)
Publish NEW gist under configured account **only if code changed**.

```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (code unchanged):
    {{< gist "aspose" "abc123" "Example.cs" >}}
    (No modification - shortcode preserved)

After Validation (code fixed):
    {{< gist "mycompany" "new_gist_789" "Example.cs" >}}
    (New gist published, shortcode updated)
```

**Requirements:**
- Environment variables: `GIST_PUBLISH_OWNER`, `GIST_PUBLISH_TOKEN`
- GitHub PAT with `gist` scope
- Optional: `GIST_PUBLISH_PUBLIC=true/false` (default: true)

**Use Case:**
- Maintaining gist references when original owner's account unavailable
- Publishing fixed code under your organization's account
- Preserving gist format while ensuring code is correct

**CLI:**
```bash
export GIST_PUBLISH_OWNER="mycompany"
export GIST_PUBLISH_TOKEN="ghp_your_token_here"
python src/cli.py patch --family zip --gist-mode upload-on-change
```

#### 5. `upload-always` (Phase 5)
Always publish NEW gist (even if code unchanged).

```markdown
Original:
    {{< gist "aspose" "abc123" "Example.cs" >}}

After Validation (always uploaded):
    {{< gist "mycompany" "new_gist_456" "Example.cs" >}}
    (New gist published, shortcode updated)
```

**Requirements:**
- Same as `upload-on-change`

**Use Case:**
- Migrating all gists to your organization's account
- Creating copies under your control
- Ensuring all gists owned by single account

**CLI:**
```bash
export GIST_PUBLISH_OWNER="mycompany"
export GIST_PUBLISH_TOKEN="ghp_your_token_here"
python src/cli.py patch --family zip --gist-mode upload-always
```

---

## Gist Replacement Rules

### 1. Shortcode Location
**How it finds the shortcode to replace:**

**Strategy 1** (Primary): Exact match from stored shortcode
- Preserved in snippet locator `notes` field during discovery
- Finds exact character-for-character match
- Most reliable (preserves whitespace, quote style)

**Strategy 2** (Fallback): Regex pattern using gist_id
- Builds pattern from `gist_id` + optional `filename`
- Tolerates whitespace variations
- Handles quoted/unquoted forms

**Example Patterns Matched:**
```
{{< gist "aspose" "abc123" >}}
{{<gist "aspose" "abc123">}}
{{< gist aspose abc123 >}}
{{< gist "aspose" "abc123" "File.cs" >}}
```

### 2. Inline Fence Format
**When replacing gist shortcode, uses this format:**

```csharp
<verified_code_content>
```

**Rules:**
- **Language marker**: Always `csharp` (explicit, not inferred)
- **Line endings**: Detected from file (`\r\n` or `\n`)
- **Indentation**: Matches surrounding markdown context
- **Whitespace**: Code content preserved exactly as verified

**Example:**
```markdown
## Example

{{< gist "aspose" "abc123" "Archive.cs" >}}

More text.
```

**Becomes:**
```markdown
## Example

```csharp
using System;
using Aspose.Zip;

class ArchiveExample {
    public static void Main() {
        // Fixed code
    }
}
```

More text.
```

### 3. Context Preservation
**What stays unchanged:**
- Headings before/after gist
- Surrounding text
- Frontmatter
- Other snippets in file
- File line endings (CRLF/LF)

---

## Change Detection

**How the system determines if a gist changed:**

```
1. Get original gist code (fetched during discovery)
2. Get verified gist code (after validation/fixes)
3. Compute SHA256 hash of each
4. Compare hashes:
   - Same hash → unchanged
   - Different hash → changed
```

**Unchanged** can mean:
- Original code compiled successfully (no fixes needed)
- OR code was already correct on GitHub

**Changed** means:
- Validation found errors
- Fixes were applied (pattern-based or Ollama)
- Verified code differs from original

---

## Dry Run Mode

**Purpose**: Preview what would be patched without modifying files.

**CLI:**
```bash
python src/cli.py patch --family zip --dry-run
```

**Output:**
- Shows which files would be modified
- Indicates which gists would be inlined
- Reports unchanged gists (preserved)
- No files actually written

**Use Cases:**
- Preview changes before committing
- Verify gist replacement logic
- Check scope of patching operation

---

## Rollback Strategy

**Before Patching:**
```bash
# Commit current state
git add .
git commit -m "Before gist patching"

# Run patch
python src/cli.py patch --family zip
```

**If Patches Are Wrong:**
```bash
# Rollback file changes
git reset --hard HEAD

# OR review specific files
git diff <file>
git checkout -- <file>
```

**Database Rollback:**
Database changes (snippet status updates) are separate from file changes.
- File rollback: `git reset`
- Database rollback: Re-run discovery to reset states

---

## Multi-Gist Pages

**Behavior**: Files with multiple gists handled independently.

**Example:**
```markdown
## Example 1
{{< gist "aspose" "gist1" >}}  (unchanged)

## Example 2
{{< gist "aspose" "gist2" >}}  (changed)
```

**After Patching:**
```markdown
## Example 1
{{< gist "aspose" "gist1" >}}  (preserved)

## Example 2
```csharp
// Inlined verified code
```
```

Each gist evaluated independently based on its change status.

---

## Edge Cases

### Gist Not Found in File
**Scenario**: Shortcode stored in DB but not found in markdown during patching.

**Possible Causes:**
- File was manually edited after discovery
- Shortcode format changed
- File moved/deleted

**Behavior:**
- Patch fails for that snippet
- Error logged: "Could not locate gist shortcode in file"
- Other snippets in file still processed

### Gist with Multiple C# Files
**Scenario**: Gist has multiple .cs files, no filename specified in shortcode.

**Discovery Behavior:**
- Marked as "ambiguous"
- Skipped during discovery (skip reason recorded)
- Not validated or patched

**Fix**: Update shortcode to specify filename:
```markdown
Before: {{< gist "aspose" "abc123" >}}
After:  {{< gist "aspose" "abc123" "Specific.cs" >}}
```

### Mixed Fence + Gist Pages
**Behavior**: Pages with both fences and gists supported.

- Fences patched normally
- Gists follow gist-mode rules
- Each snippet type independent

---

## Recommended Workflow

1. **Discovery**: Fetch gists and store real code
   ```bash
   python src/cli.py discover --family zip
   ```

2. **Validation**: Compile and fix code
   ```bash
   python src/cli.py validate --family zip
   ```

3. **Dry Run**: Preview patches
   ```bash
   python src/cli.py patch --family zip --dry-run
   ```

4. **Review**: Check dry-run output, verify gist replacement logic

5. **Patch**: Apply changes
   ```bash
   python src/cli.py patch --family zip
   ```

6. **Commit**: Save verified changes
   ```bash
   git add .
   git commit -m "Apply verified code patches (including gists)"
   ```
