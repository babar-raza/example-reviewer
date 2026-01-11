# Family Configuration Schema

**Version:** 1.0
**Status:** Canonical (as of Phase 4 implementation)

## Purpose

Family configurations define product-specific settings for discovery, validation, and patching of code examples. Each Aspose product family (ZIP, Words, PDF, Cells, etc.) requires its own configuration file.

## Schema Definition

### Canonical Format (v1.0)

```json
{
  "family": "string (required)",
  "display_name": "string (optional)",
  "content_pattern": "string (glob pattern, optional)",

  "nuget_config": {
    "primary_package": {
      "name": "string (required)",
      "version_strategy": "latest_stable | pinned",
      "pinned_version": "string (required if version_strategy=pinned)"
    },
    "additional_packages": [
      {
        "name": "string",
        "version": "string"
      }
    ],
    "target_frameworks": ["string (e.g., net8.0, net6.0)"]
  },

  "code_defaults": {
    "default_usings": ["string (namespace names)"]
  },

  "patterns": [],
  "non_existent_apis": []
}
```

### Field Descriptions

#### Top-Level Fields

- **family** (required, string): Short identifier for the product family. Used for directory names and database keys. Example: `"zip"`, `"words"`, `"pdf"`.

- **display_name** (optional, string): Human-readable name for UI/reporting. Example: `"Aspose.ZIP for .NET"`.

- **content_pattern** (optional, string): Glob pattern to filter markdown files during discovery. Example: `"**/zip/**/*.md"`. If omitted, discovers all markdown files.

#### nuget_config

Configuration for NuGet packages required for compilation.

- **primary_package.name** (required, string): Main NuGet package for this family. Example: `"Aspose.Zip"`, `"Newtonsoft.Json"`.

- **primary_package.version_strategy** (required, string):   - `"latest_stable"`: Resolve to latest stable version from NuGet API
  - `"pinned"`: Use specific version from `pinned_version` field

- **primary_package.pinned_version** (conditional, string): Required if `version_strategy` is `"pinned"`. Example: `"24.12.0"`.

- **additional_packages** (optional, array): Additional NuGet packages to install. Each entry has `name` and `version` fields.

- **target_frameworks** (optional, array): List of .NET target frameworks. Defaults to `["net8.0"]`. Example: `["net8.0", "net6.0"]`.

#### code_defaults

Default code generation settings.

- **default_usings** (optional, array): Default `using` directives to inject into generated validator Program.cs. Example: `["System.IO", "Aspose.Zip", "Aspose.Zip.Saving"]`.

#### Other Fields

- **patterns** (optional, array): Pattern-based fix rules (legacy, may be deprecated).

- **non_existent_apis** (optional, array): Known non-existent APIs to warn about (legacy, may be deprecated).

## Backward Compatibility

### Legacy Format (pre-Phase 4)

Old configs used a flat structure:

```json
{
  "name": "test",
  "package_id": "Newtonsoft.Json",
  "version": "latest_stable",
  "target_framework": "net6.0",
  "skip_patterns": [],
  "ollama_enabled": false
}
```

### Migration Strategy

The system provides `normalize_family_config()` to convert legacy configs at runtime:

**Mapping:**
- `name` → `family`
- `package_id` → `nuget_config.primary_package.name`
- `version` → `nuget_config.primary_package.version_strategy`
- `target_framework` (singular) → `target_frameworks` (array)
- `skip_patterns`, `ollama_enabled` → ignored (deprecated)

## Examples

### Example 1: Aspose.ZIP with Latest Stable

```json
{
  "family": "zip",
  "display_name": "Aspose.ZIP for .NET",
  "content_pattern": "**/zip/**/*.md",
  "nuget_config": {
    "primary_package": {
      "name": "Aspose.Zip",
      "version_strategy": "latest_stable"
    },
    "target_frameworks": ["net8.0"]
  },
  "code_defaults": {
    "default_usings": [
      "Aspose.Zip",
      "Aspose.Zip.Saving",
      "Aspose.Zip.SevenZip",
      "Aspose.Zip.Bzip2",
      "Aspose.Zip.Gzip"
    ]
  },
  "patterns": [],
  "non_existent_apis": ["SaveAsync", "CreateEntryAsync"]
}
```

### Example 2: Pinned Version with Additional Packages

```json
{
  "family": "words",
  "display_name": "Aspose.Words for .NET",
  "content_pattern": "**/words/**/*.md",
  "nuget_config": {
    "primary_package": {
      "name": "Aspose.Words",
      "version_strategy": "pinned",
      "pinned_version": "24.1.0"
    },
    "additional_packages": [
      {
        "name": "System.Drawing.Common",
        "version": "8.0.0"
      }
    ],
    "target_frameworks": ["net8.0", "net6.0"]
  },
  "code_defaults": {
    "default_usings": [
      "Aspose.Words",
      "Aspose.Words.Saving",
      "Aspose.Words.Tables"
    ]
  },
  "patterns": [],
  "non_existent_apis": []
}
```

### Example 3: Test/Smoke (Minimal)

```json
{
  "family": "smoke",
  "display_name": "Smoke Test Family",
  "content_pattern": "**/smoke/**/*.md",
  "nuget_config": {
    "primary_package": {
      "name": "Newtonsoft.Json",
      "version_strategy": "latest_stable"
    },
    "target_frameworks": ["net8.0"]
  },
  "code_defaults": {
    "default_usings": ["Newtonsoft.Json"]
  },
  "patterns": [],
  "non_existent_apis": []
}
```

## Validation Rules

1. **family** must be non-empty and contain only lowercase alphanumeric characters and hyphens.
2. **nuget_config.primary_package.name** must be a valid NuGet package identifier.
3. If **version_strategy** is `"pinned"`, **pinned_version** must be provided.
4. **target_frameworks** must contain at least one valid .NET target framework moniker.
5. **default_usings** should contain valid C# namespace names (no validation enforced, but recommended).

## Future Enhancements

- JSON Schema validation
- Config linting tool
- Migration tool to convert legacy configs
- Support for multiple languages (not just C#)

## Related Files

- `config/families/smoke.json` - Reference canonical implementation
- `config/families/test.json` - Legacy format example
- `config/families/zip.json` - Production Aspose.ZIP config (Phase 4)
- `src/workspace_manager.py` - Consumes these configs
- `src/cli.py` - Loads configs for commands

## Change History

- **2026-01-11 (Phase 4)**: Initial canonical schema defined
- **Pre-Phase 4**: Legacy flat format in use
