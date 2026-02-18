# Patching Strategies

## Overview

The patching system updates original markdown files with verified code snippets using a cascading strategy approach. It locates the exact position of the original code fence and replaces it with verified code while preserving markdown structure.

## Cascading Strategy Pattern

The system tries three strategies in order of reliability:

```
Strategy 1: Content Hash Match
    |-- SHA256 exact match (most reliable, O(n))
    |-- ~70% success rate on unmodified files
    |
    v (if no match)
Strategy 2: Heading Context Match
    |-- Structural matching by headings + ordinal
    |-- Handles minor code edits
    |-- ~20% success rate when Strategy 1 fails
    |
    v (if no match)
Strategy 3: Fuzzy Similarity Match
    |-- Normalized Levenshtein distance
    |-- Threshold: 0.7 similarity
    |-- Last resort (~8% when Strategy 2 fails)
    |
    v (all failed)
Report error (fence not found)
```

## Strategy 1: Content Hash Match

Computes SHA256 of each C# code fence in the file and compares against the stored hash from discovery time.

**Succeeds when:** File content unchanged since discovery.
**Fails when:** File manually edited, whitespace changed, or code modified.

## Strategy 2: Heading Context Match

Uses document structure (heading hierarchy) and snippet ordinal position to locate the correct fence.

During discovery, each snippet records:
- `heading_context`: list of parent headings (e.g., `["Installation", "Using NuGet"]`)
- `snippet_ordinal`: position among C# fences under that heading

**Succeeds when:** Heading structure and snippet position unchanged.
**Fails when:** Headings renamed/reordered or new fences inserted before the target.

## Strategy 3: Fuzzy Similarity Match

Normalizes code (removes comments, whitespace, lowercases) and computes Levenshtein distance between original and each candidate fence.

**Threshold:** 0.7 similarity (empirically chosen).
- Below 0.6: too many false positives
- Above 0.8: too many false negatives

## Fence Pattern

```python
fence_pattern = r'(```(?:csharp|cs|c#|dotnet|net))\s*\n(.*?)\n(```)'
```

Language tag is **required** (not optional) to prevent matching closing fences of other languages.

## Patch Application

Patches use direct string replacement with no HTML markers (Hugo compatibility):

````
```{language}
{verified_code}
```
````

## Post-Patch Verification

After patching, the system verifies that the verified code appears inside a proper C# fence in the modified file. Only checks fence containment - does not flag inline code references in prose.

## Dry-Run Mode

Use `--dry-run` to preview patches without modifying files:

```bash
python -m src.cli.main md-update --family zip --dry-run --allow-md-write
```

## Performance

| Strategy | Time Complexity | Success Rate | Use Case |
|----------|----------------|--------------|----------|
| Hash     | O(n)           | ~70%         | Unchanged files |
| Context  | O(n*m)         | ~20%         | Minor edits |
| Fuzzy    | O(n*m^2)       | ~8%          | Last resort |

Where n = number of fences, m = average fence length.

## Edge Cases

- **Identical snippets**: Disambiguated by heading context + ordinal
- **Nested fences**: Non-greedy regex stops at first closing fence
- **Empty fences**: Pattern requires content between newlines, won't match empty

## See Also

- [pipeline.md](pipeline.md) - Full pipeline phases
- [safety.md](safety.md) - Safety mechanisms
