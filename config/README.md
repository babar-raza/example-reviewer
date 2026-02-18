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
