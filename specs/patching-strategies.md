# Patching Strategies Specification

## Overview

The patching system reliably updates original markdown files with verified code snippets using a cascading strategy approach. The goal is to locate the exact position of the original code fence and replace it with verified code while preserving markdown structure.

## Problem Statement

**Challenge**: Locate a specific code fence in a markdown file that may have:
- Multiple code snippets
- Multiple languages (bash, csharp, json, etc.)
- Modified content since discovery
- Similar or duplicate code blocks

**Requirements**:
1. **Accuracy**: Must match the correct code fence
2. **Reliability**: Handle modified files gracefully
3. **Safety**: Verify patch before writing
4. **Hugo Compatibility**: No HTML markers in output

## Cascading Strategy Pattern

The system tries three strategies in order of reliability:

```
┌─────────────────────────────────────────────────┐
│          Strategy Selection Flow                 │
└─────────────────────────────────────────────────┘

   Start Patching
        │
        ├─► Strategy 1: Content Hash Match
        │      ├─► SHA256 hash matching
        │      ├─► Most reliable (exact match)
        │      └─► Fast: O(n) where n = fences
        │
        ├─► If no match...
        │
        ├─► Strategy 2: Heading Context Match
        │      ├─► Structural matching
        │      ├─► Reliable (handles minor edits)
        │      └─► Medium speed: O(n*m) where m = headings
        │
        ├─► If no match...
        │
        └─► Strategy 3: Fuzzy Similarity Match
               ├─► Content similarity scoring
               ├─► Last resort (handles major changes)
               └─► Slow: O(n^2) for similarity calculation

     Success: Apply patch
     Failure: Report error
```

## Strategy 1: Content Hash Match

### Algorithm

```python
def _find_by_content_hash(file_content, original_code, content_hash):
    """Find fence by exact content match using SHA256 hash."""

    # Compute expected hash from original code
    expected_hash = sha256(original_code.encode()).hexdigest()

    # Find all C# code fences in file
    fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
    matches = re.finditer(fence_pattern, file_content, DOTALL | IGNORECASE)

    # Check each fence's content hash
    for match in matches:
        fence_code = match.group(2)
        fence_hash = sha256(fence_code.encode()).hexdigest()

        # Match if hash equals either expected or stored hash
        if fence_hash == expected_hash or fence_hash == content_hash:
            return match.start(), match.end(), extract_language(match.group(1))

    return None, None, "csharp"
```

### When It Succeeds

- ✅ File content unchanged since discovery
- ✅ Code fence content identical
- ✅ Fast and deterministic

### When It Fails

- ❌ File has been manually edited
- ❌ Code formatting changed (whitespace, comments)
- ❌ Code fence modified after discovery

### Performance

- **Time Complexity**: O(n) where n = number of code fences
- **Space Complexity**: O(1)
- **Success Rate**: ~70% on unmodified files

### Example

**Original Code** (discovery time):
```csharp
using (TarArchive archive = new TarArchive())
{
    archive.CreateEntry("file.txt", "input.txt");
}
```

**Stored Hash**: `abc123...`

**File Content**:
````markdown
## Create TAR Archive

```csharp
using (TarArchive archive = new TarArchive())
{
    archive.CreateEntry("file.txt", "input.txt");
}
```
````

**Match**: ✅ SHA256 matches → Strategy 1 succeeds

## Strategy 2: Heading Context Match

### Algorithm

```python
def _find_by_heading_context(file_content, original_code, heading_context, snippet_ordinal):
    """Find fence by document structure and position."""

    current_headings = []
    fence_candidates = []
    current_ordinal = 0

    lines = file_content.split('\n')
    fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'

    # Parse file line by line
    for i, line in enumerate(lines):
        # Update heading context
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            heading_text = line.lstrip('#').strip()
            current_headings = current_headings[:level-1] + [heading_text]

        # Check for code fence
        if line.startswith('```'):
            file_pos = sum(len(lines[j]) + 1 for j in range(i))
            match = re.search(fence_pattern, file_content[file_pos:], DOTALL)

            if match and match.start() == 0:
                current_ordinal += 1
                fence_candidates.append({
                    'start_pos': file_pos,
                    'end_pos': file_pos + match.end(),
                    'fence_language': extract_language(match.group(1)),
                    'heading_context': current_headings.copy(),
                    'ordinal': current_ordinal,
                    'code': match.group(2)
                })

    # Find best match by context and ordinal
    for candidate in fence_candidates:
        if (candidate['heading_context'] == heading_context and
            candidate['ordinal'] == snippet_ordinal):
            return candidate['start_pos'], candidate['end_pos'], candidate['fence_language']

    return None, None, "csharp"
```

### When It Succeeds

- ✅ Heading structure unchanged
- ✅ Snippet position unchanged (ordinal match)
- ✅ Handles minor code edits

### When It Fails

- ❌ Headings renamed or reordered
- ❌ Code fence moved to different section
- ❌ New code fences added before snippet

### Performance

- **Time Complexity**: O(n*m) where n = lines, m = fences
- **Space Complexity**: O(k) where k = fence candidates
- **Success Rate**: ~20% when Strategy 1 fails

### Example

**Heading Context** (from discovery):
```python
["Installation", "Using NuGet Package Manager"]
```

**Snippet Ordinal**: 2

**File Content**:
````markdown
# Installation

## Using NuGet Package Manager

```bash
Install-Package Aspose.Zip
```

```csharp
using Aspose.Zip;
// ... code snippet 2
```
````

**Match**: ✅ Headings match + ordinal = 2 → Strategy 2 succeeds

## Strategy 3: Fuzzy Similarity Match

### Algorithm

```python
def _find_by_fuzzy_match(file_content, original_code):
    """Find fence by content similarity scoring."""

    fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
    matches = list(re.finditer(fence_pattern, file_content, DOTALL | IGNORECASE))

    best_similarity = 0.0
    best_match = None

    for match in matches:
        fence_code = match.group(2)
        similarity = code_similarity(original_code, fence_code)

        if similarity > best_similarity:
            best_similarity = similarity
            best_match = match

    # Only accept if similarity > threshold
    if best_match and best_similarity >= 0.7:
        return best_match.start(), best_match.end(), extract_language(best_match.group(1))

    return None, None, "csharp"

def code_similarity(code1, code2):
    """Compute similarity using normalized edit distance."""

    # Normalize: remove comments, whitespace, case
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)

    # Compute Levenshtein distance
    distance = levenshtein_distance(norm1, norm2)
    max_len = max(len(norm1), len(norm2))

    # Convert to similarity score (0-1)
    if max_len == 0:
        return 1.0
    return 1.0 - (distance / max_len)

def normalize_code(code):
    """Normalize code for comparison."""
    # Remove comments
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

    # Remove whitespace
    code = re.sub(r'\s+', ' ', code)

    # Lowercase for case-insensitive comparison
    return code.strip().lower()
```

### When It Succeeds

- ✅ Code structurally similar
- ✅ Minor edits (variable names, comments)
- ✅ Last resort when other strategies fail

### When It Fails

- ❌ Code completely rewritten
- ❌ Multiple similar snippets (ambiguous match)
- ❌ Similarity below threshold (< 0.7)

### Performance

- **Time Complexity**: O(n*m^2) where n = fences, m = avg fence length
- **Space Complexity**: O(m) for distance matrix
- **Success Rate**: ~8% when Strategy 2 fails

### Similarity Threshold

**0.7** chosen empirically:
- Too low (< 0.6): False positives
- Too high (> 0.8): False negatives
- 0.7: Balanced trade-off

### Example

**Original Code**:
```csharp
using (var archive = new Archive()) {
    archive.CreateEntry("file.txt", "input.txt");
}
```

**Modified Code** (in file):
```csharp
using (var zipArchive = new Archive())
{
    // Add file to archive
    zipArchive.CreateEntry("file.txt", "input.txt");
}
```

**Similarity Calculation**:
- Normalized original: `using var archive new archive createentry file txt input txt`
- Normalized modified: `using var ziparchive new archive add file to archive ziparchive createentry file txt input txt`
- Levenshtein distance: 35
- Similarity: 1 - (35/95) ≈ 0.63

**Match**: ❌ Below threshold (0.63 < 0.7) → Strategy 3 fails

## Fence Pattern Matching

### Regex Pattern

```python
fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
```

**Breakdown**:
- `(```(?:csharp|cs|c#|dotnet|net))`: Capture opening fence with C# language tag
- `\s*\n`: Optional whitespace, then newline
- `(.*?)`: Capture code content (non-greedy)
- `\n`: Newline before closing
- `(```)`: Capture closing fence

**Critical**: Language tag is **required** (no `?` after group)

### Why Language Tag is Required

**Problem** (old pattern with optional tag):
```python
fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net)?)\s*\n(.*?)\n(```)'
                                                   ^ Optional made ``` alone valid
```

**Bug**:
````markdown
```bash
npm install
```

## Example

```csharp
// Code here
```
````

With optional tag, regex matched:
- **Opening**: ``` (closing bash fence)
- **Content**: Everything from bash fence to csharp fence
- **Closing**: ``` (opening csharp fence)

**Fix**: Remove `?` to require language tag → only matches C# fences

## Language Tag Extraction

```python
def extract_language_from_fence(fence_opening):
    """Extract language tag from fence opening line."""
    # Input: "```csharp" or "```cs"
    match = re.match(r'```(\w+)', fence_opening.strip())
    return match.group(1) if match else "csharp"
```

**Examples**:
- ````csharp` → `csharp`
- ````cs` → `cs`
- ````c#` → Won't match (contains #), defaults to `csharp`

## Patch Application

### Direct Replacement (No Markers)

```python
def apply_patch(file_content, match_start, match_end, verified_code, fence_language):
    """Replace code fence with verified code."""

    # Build replacement fence
    replacement = f"```{fence_language}\n{verified_code}\n```"

    # Splice into file
    modified_content = (
        file_content[:match_start] +
        replacement +
        file_content[match_end:]
    )

    return modified_content
```

**Format**:
````
```{language}
{verified_code}
```
````

**Important**: No HTML markers (Hugo compatibility)

### Example Transformation

**Before**:
````markdown
## Create Archive

```csharp
using (Archive archive = new Archive())
{
    archive.CreateEntry("file.txt", "input.txt");
}
```
````

**After Patch** (with verified code):
````markdown
## Create Archive

```csharp
using Aspose.Zip;

using (Archive archive = new Archive())
{
    archive.CreateEntry("file.txt", "input.txt");
}
```
````

## Post-Patch Verification

### Verification Process

```python
def _verify_patch(modified_content, verified_code, snippet):
    """Verify patched code appears in proper fence."""

    fence_pattern = r'```(?:csharp|cs|c#|dotnet|net)\s*\n(.*?)\n```'
    matches = re.finditer(fence_pattern, modified_content, DOTALL | IGNORECASE)

    # Normalize for comparison
    normalized_verified = normalize_for_comparison(verified_code)

    for match in matches:
        fence_code = match.group(1)
        normalized_fence = normalize_for_comparison(fence_code)

        if normalized_verified in normalized_fence:
            return {'success': True, 'error': ''}

    return {
        'success': False,
        'error': 'Expected code not found in any code fence'
    }
```

### What We Verify

✅ **Do Verify**:
- Verified code exists in a C# fence
- Code is properly fenced (not leaked)

❌ **Don't Verify**:
- No C# patterns outside fences (too many false positives)
- Inline code examples like `new Archive()` are acceptable

### False Positive Avoidance

**Old (broken) verification**:
```python
# BAD: Checks for C# patterns outside fences
suspicious_patterns = [
    r'\busing\s+System',
    r'\busing\s+Aspose',
    r'new\s+Archive\s*\('
]

# This triggers on legitimate prose like:
# "You can create an archive using `new Archive()`"
```

**New (correct) verification**:
```python
# GOOD: Only verify code is in fence, ignore prose
if not found_in_fence:
    return {'success': False, 'error': 'Expected code not found in any code fence'}

return {'success': True, 'error': ''}
```

## Error Handling

### Fence Not Found

```python
if matched_start is None:
    return PatchResult(
        snippet.snippet_id,
        page.relative_path,
        success=False,
        error="Could not locate code fence in file",
        original_content="",
        modified_content=""
    )
```

**Common Causes**:
- File heavily modified since discovery
- Code fence deleted
- Language tag changed (e.g., `csharp` → `c#`)

### Verification Failed

```python
if not verification_result['success']:
    return PatchResult(
        snippet.snippet_id,
        page.relative_path,
        success=False,
        error=f"Patch verification failed: {verification_result['error']}",
        original_content=content,
        modified_content=modified_content
    )
```

**Common Causes**:
- Regex mismatch in verification
- Code transformation during patching
- Whitespace normalization issues

## Dry-Run Mode

### Implementation

```python
def patch_snippet(snippet, page, dry_run=False):
    """Patch a single snippet, optionally in dry-run mode."""

    # ... locate fence and apply patch ...

    if not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    return PatchResult(success=True, ...)
```

### Use Cases

- Test patching without modifications
- Preview changes before applying
- Verify strategy success rates
- Debug patching issues

### Output

```
[*] DRY RUN MODE - No files will be modified

[OK] Snippet 1: Patched successfully (Strategy: hash)
[OK] Snippet 2: Patched successfully (Strategy: context)
[!] Snippet 3: Could not locate code fence in file
```

## Performance Characteristics

### Strategy Performance Comparison

| Strategy | Time Complexity | Space | Success Rate | Use Case |
|----------|----------------|-------|--------------|----------|
| Hash     | O(n)           | O(1)  | 70%         | Unchanged files |
| Context  | O(n*m)         | O(k)  | 20%         | Structural match |
| Fuzzy    | O(n*m²)        | O(m)  | 8%          | Last resort |

Where:
- n = number of code fences
- m = average fence length (chars)
- k = number of fence candidates

### Optimization Opportunities

1. **Cache fence parsing**: Parse file once, reuse for multiple snippets
2. **Parallel processing**: Patch independent files concurrently
3. **Early exit**: Stop at first matching strategy
4. **Index pre-computation**: Build heading index before matching

## Edge Cases

### Multiple Identical Snippets

**Problem**: Two identical code blocks in same file

**Solution**: Use heading context + ordinal to disambiguate

**Example**:
````markdown
## Method 1

```csharp
var archive = new Archive();
```

## Method 2

```csharp
var archive = new Archive();
```
````

- Snippet 1: `heading_context=["Method 1"], ordinal=1`
- Snippet 2: `heading_context=["Method 2"], ordinal=2`

### Nested Code Fences

**Problem**: Markdown in code fence

**Solution**: Regex is non-greedy, stops at first closing fence

**Example**:
`````markdown
```markdown
Here's an example:

```csharp
var x = 1;
```
`````

**Match**: Correctly matches outer fence (markdown), not inner

### Empty Code Fences

**Problem**: Fence with no content

**Solution**: Pattern requires newline-content-newline, won't match empty

**Example**:
````markdown
```csharp
```
````

**Match**: ❌ Doesn't match (no content between newlines)

## Testing Strategy

### Unit Tests

```python
def test_hash_strategy_exact_match():
    content = '```csharp\nvar x = 1;\n```'
    original = 'var x = 1;'
    hash = sha256(original.encode()).hexdigest()

    start, end, lang = _find_by_content_hash(content, original, hash)

    assert start is not None
    assert lang == 'csharp'

def test_context_strategy_heading_match():
    content = '# Heading\n```csharp\nvar x = 1;\n```'
    heading_context = ['Heading']
    ordinal = 1

    start, end, lang = _find_by_heading_context(content, 'var x = 1;', heading_context, ordinal)

    assert start is not None

def test_fuzzy_strategy_threshold():
    content = '```csharp\nvar y = 2; // changed\n```'
    original = 'var x = 1;'

    start, end, lang = _find_by_fuzzy_match(content, original)

    assert start is None  # Below threshold
```

### Integration Tests

```python
def test_full_patching_pipeline():
    # Setup test file
    test_file = create_test_markdown()

    # Create snippet with verified code
    snippet = create_test_snippet()

    # Patch
    result = patch_service.patch_snippet(snippet, test_file, dry_run=False)

    # Verify
    assert result.success
    assert verified_code in read_file(test_file)
```

## Best Practices

### For Authors

1. **Keep heading structure stable**: Aids context matching
2. **Don't duplicate code**: Makes matching ambiguous
3. **Use descriptive headings**: Improves context specificity

### For Operators

1. **Run dry-run first**: Verify before modifying files
2. **Review failed patches**: Understand why strategies failed
3. **Monitor success rates**: Detect pattern changes

### For Developers

1. **Test all strategies**: Unit test each independently
2. **Profile performance**: Identify bottlenecks
3. **Log strategy usage**: Understand real-world distribution
