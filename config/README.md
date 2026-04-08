# config/ - Configuration

Pipeline configuration files.

## Files

- `global.json` - Global settings: LLM provider, database paths, telemetry, auto-learn, timeouts

## Subdirectories

- `families/` - Per-family configuration (one JSON per Aspose product family)

## Family Config Structure

Each family JSON (e.g., `zip.json`, `words.json`) contains:

- `content_roots` - Directories containing markdown blog posts
- `nuget_package` / `nuget_version` - NuGet package for compilation
- `safe_usings` - C# using directives always safe to add
- `api_catalog` - Path to assembly-reflected API catalog
- `fixture_resolver` - Test data generation settings
- `learned_patterns` - Auto-learn pattern database path
- `compilation` / `runtime` - Timeout and retry settings

## Family Knowledge-Base Extensions

In addition to the standard `{family}.json`, a family may optionally provide
two KB extension files that activate additional pipeline phases:

### `{family}_review_hints.json`  — LLM Guidance Layer

Injects human-curated API misuse warnings into LLM review prompts. When a hint
matches the code being reviewed, the LLM is instructed to flag it **even if the
article prose argues the approach is correct**.

**Required fields per hint:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (e.g. `"words-01"`) |
| `hint` | string | Warning text injected into the LLM prompt |

**Optional fields:**
| Field | Type | Description |
|-------|------|-------------|
| `pattern` | string | Substring that must appear in code for this hint to activate |
| `context` | string | Substring that must appear in article intent/content (case-insensitive) |
| `issue_type` | string | Categorisation label (e.g. `"semantic_misuse"`, `"outdated_api"`) |
| `detection_keywords` | array[string] | Keywords used during proactive audit phase filtering |
| `correction` | string | Suggested fix text |
| `content_types` | array[string] | Restrict hint to specific content types (e.g. `["kb", "blog"]`) |

A missing file is valid — the family simply has no LLM guidance layer yet.
A present but structurally broken file raises `KBLoadError` and is logged at ERROR level.

### `{family}_behavioral_patterns.json`  — Deterministic Enforcement Layer

Regex-based patterns evaluated against code **without** an LLM. Patterns with
`severity: "error"` are blocking: they gate pipeline output and can trigger
the deterministic fix-and-rescan loop.

**Required fields per pattern:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (e.g. `"words_write_protection_not_encryption"`) |
| `severity` | `"error"` \| `"warning"` \| `"critical"` | `"error"` and `"critical"` are blocking |
| `description` | string | Human-readable description of the issue |

At least one of `code_regex` or `required_regex` must also be present.

**Optional fields:**
| Field | Type | Description |
|-------|------|-------------|
| `code_regex` | string | Fires when this regex **matches** the code (presence detection) |
| `required_regex` | string | Fires when this regex is **absent** from the code (absence detection) |
| `missing_regex` | string | Combined with `code_regex`: fires only when this regex is also **absent** |
| `intent_keywords` | array[string] | Pattern fires only when at least one keyword appears in article intent/content |
| `context_keywords` | array[string] | Additional context filter (any must match) |
| `content_types` | array[string] | Restrict pattern to specific content types |
| `issue_type` | string | Categorisation label |
| `suggestion` | string | Suggested fix text surfaced in findings |

All regex fields are compiled at load time — an invalid regex raises `KBLoadError` immediately.
A missing file is valid. A present but broken file logs at ERROR level and disables enforcement
for that family.

### Validation

Use the CLI tool to validate KB files before committing:

```bash
# Validate all families
python scripts/validate_kb.py --all

# Validate a single family
python scripts/validate_kb.py --family words
```

Exit code 0 = all files valid. Exit code 1 = at least one file is broken.
