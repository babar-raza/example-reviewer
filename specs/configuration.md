# Configuration Specification

## Overview

The Example Reviewer system can be configured through environment variables, configuration files, and command-line arguments.

## Configuration Hierarchy

Configuration is resolved in this order (highest priority first):

1. **Command-line arguments**: Explicit flags override everything
2. **Environment variables**: System-wide configuration
3. **Configuration files**: Project-specific settings
4. **Defaults**: Hard-coded fallback values

---

## Environment Variables

### Database Configuration

#### `DATABASE_PATH`

Path to SQLite database file.

```bash
export DATABASE_PATH="/path/to/snippets.db"
```

- **Default**: `data/snippets.db`
- **Type**: String (file path)
- **Example**: `/var/lib/example-reviewer/snippets.db`

### Content Configuration

#### `CONTENT_ROOT`

Root directory containing markdown files.

```bash
export CONTENT_ROOT="/path/to/content"
```

- **Default**: `../../content` (relative to script)
- **Type**: String (directory path)
- **Example**: `/home/user/aspose.net/content`

### Workspace Configuration

#### `WORKSPACE_BASE_PATH`

Directory for temporary compilation workspaces.

```bash
export WORKSPACE_BASE_PATH="/tmp/example-reviewer-workspaces"
```

- **Default**: `workspaces`
- **Type**: String (directory path)
- **Example**: `/tmp/example-reviewer-workspaces`

#### `WORKSPACE_CLEANUP_AUTO`

Automatically cleanup workspaces after validation.

```bash
export WORKSPACE_CLEANUP_AUTO="true"
```

- **Default**: `false`
- **Type**: Boolean (`true`|`false`)
- **Note**: Set to `true` to save disk space

### Ollama Configuration

#### `OLLAMA_URL`

Ollama API endpoint URL.

```bash
export OLLAMA_URL="http://localhost:11434"
```

- **Default**: `http://localhost:11434`
- **Type**: String (URL)
- **Example**: `http://192.168.1.100:11434`

#### `OLLAMA_MODEL`

Ollama model to use for code fixing.

```bash
export OLLAMA_MODEL="codellama"
```

- **Default**: `llama3.1`
- **Type**: String (model name)
- **Options**: `llama3.1`, `codellama`, `deepseek-coder`, etc.

#### `OLLAMA_TIMEOUT`

Timeout for Ollama API requests (seconds).

```bash
export OLLAMA_TIMEOUT="60"
```

- **Default**: `30`
- **Type**: Integer (seconds)
- **Range**: 10-300

#### `OLLAMA_TEMPERATURE`

Temperature for LLM generation (0 = deterministic).

```bash
export OLLAMA_TEMPERATURE="0"
```

- **Default**: `0`
- **Type**: Float
- **Range**: 0.0-1.0
- **Note**: Higher = more creative, lower = more deterministic

### Compilation Configuration

#### `DOTNET_FRAMEWORK`

Target .NET framework version.

```bash
export DOTNET_FRAMEWORK="net8.0"
```

- **Default**: `net8.0`
- **Type**: String
- **Options**: `net6.0`, `net7.0`, `net8.0`

#### `ASPOSE_ZIP_VERSION`

Aspose.Zip NuGet package version.

```bash
export ASPOSE_ZIP_VERSION="24.11.0"
```

- **Default**: Latest version (determined at runtime)
- **Type**: String (semantic version)
- **Example**: `24.11.0`

#### `COMPILATION_TIMEOUT`

Timeout for dotnet build (seconds).

```bash
export COMPILATION_TIMEOUT="60"
```

- **Default**: `30`
- **Type**: Integer (seconds)
- **Range**: 10-300

### Logging Configuration

#### `LOG_LEVEL`

Logging verbosity level.

```bash
export LOG_LEVEL="DEBUG"
```

- **Default**: `INFO`
- **Type**: String
- **Options**: `DEBUG`, `INFO`, `WARN`, `ERROR`

#### `LOG_FILE_PATH`

Path to log file.

```bash
export LOG_FILE_PATH="/var/log/example-reviewer.log"
```

- **Default**: `logs/example-reviewer.log`
- **Type**: String (file path)

#### `LOG_CONSOLE_COLORS`

Enable colored console output.

```bash
export LOG_CONSOLE_COLORS="false"
```

- **Default**: `true`
- **Type**: Boolean
- **Note**: Disable for non-TTY environments

### Pattern Registry Configuration

#### `PATTERN_REGISTRY_PATH`

Path to custom pattern registry file.

```bash
export PATTERN_REGISTRY_PATH="/etc/example-reviewer/patterns.json"
```

- **Default**: Built-in patterns
- **Type**: String (file path)
- **Format**: JSON

---

## Configuration File

### Format: config/settings.json

```json
{
  "database": {
    "path": "data/snippets.db",
    "connection_pool_size": 5,
    "timeout": 30
  },
  "content": {
    "root": "../../content",
    "families": {
      "zip": {
        "pattern": "**/zip/**/*.md",
        "nuget_packages": ["Aspose.Zip"]
      },
      "pdf": {
        "pattern": "**/pdf/**/*.md",
        "nuget_packages": ["Aspose.PDF"]
      }
    }
  },
  "workspaces": {
    "base_path": "workspaces",
    "cleanup_auto": false,
    "max_concurrent": 4
  },
  "ollama": {
    "url": "http://localhost:11434",
    "model": "llama3.1",
    "timeout": 30,
    "temperature": 0,
    "max_retries": 3
  },
  "compilation": {
    "framework": "net8.0",
    "timeout": 30,
    "parallel_builds": false
  },
  "logging": {
    "level": "INFO",
    "file": "logs/example-reviewer.log",
    "console_colors": true,
    "format": "%(asctime)s [%(levelname)s] %(message)s"
  },
  "patching": {
    "dry_run_default": true,
    "verify_patches": true,
    "fuzzy_threshold": 0.7
  }
}
```

### Loading Configuration

```python
import json
from pathlib import Path

def load_config():
    config_path = Path("config/settings.json")
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}

config = load_config()
database_path = config.get("database", {}).get("path", "data/snippets.db")
```

---

## Family Configuration

### config/families.json

Define product families and their settings.

```json
{
  "zip": {
    "display_name": "Aspose.ZIP for .NET",
    "content_pattern": "**/zip/**/*.md",
    "nuget_packages": [
      {"name": "Aspose.Zip", "version": "24.11.0"}
    ],
    "using_statements": [
      "using Aspose.Zip;",
      "using Aspose.Zip.Saving;",
      "using Aspose.Zip.Tar;"
    ],
    "pattern_fixes": [
      {
        "name": "Add using directive",
        "error_pattern": "CS0246.*'Archive'",
        "old_pattern": "^",
        "new_pattern": "using Aspose.Zip;\\n"
      }
    ]
  },
  "pdf": {
    "display_name": "Aspose.PDF for .NET",
    "content_pattern": "**/pdf/**/*.md",
    "nuget_packages": [
      {"name": "Aspose.PDF", "version": "24.11.0"}
    ],
    "using_statements": [
      "using Aspose.Pdf;",
      "using Aspose.Pdf.Text;"
    ],
    "pattern_fixes": []
  }
}
```

---

## Command-Line Arguments

### Global Options

Available for all commands:

```bash
python src/cli.py <command> [options]
```

#### `--database PATH`

Override database path.

```bash
python src/cli.py discover --family zip --database /tmp/test.db
```

#### `--content-root PATH`

Override content root directory.

```bash
python src/cli.py discover --family zip --content-root /path/to/content
```

#### `--verbose` / `-v`

Enable verbose logging (DEBUG level).

```bash
python src/cli.py validate --family zip -v
```

#### `--quiet` / `-q`

Suppress all output except errors.

```bash
python src/cli.py patch --family zip -q
```

### Command-Specific Options

#### discover

```bash
python src/cli.py discover --family FAMILY [--force]
```

- `--family`: Product family (required)
- `--force`: Re-discover even if already scanned

#### validate

```bash
python src/cli.py validate --family FAMILY [--run-id ID] [--parallel]
```

- `--family`: Product family (required)
- `--run-id`: Specific run to validate
- `--parallel`: Enable parallel validation (experimental)

#### fix

```bash
python src/cli.py fix --family FAMILY [--snippet-id ID] [--max-attempts N]
```

- `--family`: Product family (required)
- `--snippet-id`: Fix specific snippet
- `--max-attempts`: Max fix iterations (default: 3)

#### patch

```bash
python src/cli.py patch --family FAMILY [--dry-run] [--verify]
```

- `--family`: Product family (required)
- `--dry-run`: Preview without modifying files
- `--verify`: Enable post-patch verification (default: true)

---

## Pattern Registry Configuration

### Custom Pattern File

Create `config/custom_patterns.json`:

```json
{
  "zip": [
    {
      "name": "Fix DeflateCompressionSettings constructor",
      "description": "Remove CompressionLevel parameter",
      "error_pattern": "CS1729.*'DeflateCompressionSettings'.*does not take 1 arguments",
      "old_pattern": "new DeflateCompressionSettings\\(CompressionLevel\\.\\w+\\)",
      "new_pattern": "new DeflateCompressionSettings()"
    },
    {
      "name": "Add using Aspose.Zip.Tar",
      "description": "Add TAR namespace",
      "error_pattern": "CS0246.*'TarArchive'",
      "old_pattern": "^",
      "new_pattern": "using Aspose.Zip.Tar;\\n"
    }
  ]
}
```

Load custom patterns:

```bash
export PATTERN_REGISTRY_PATH="config/custom_patterns.json"
python src/cli.py validate --family zip
```

---

## Workspace Template Configuration

### Custom .csproj Template

Create `config/validator.csproj.template`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>{{ framework }}</TargetFramework>
    <OutputType>Library</OutputType>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    {% for package in packages %}
    <PackageReference Include="{{ package.name }}" Version="{{ package.version }}" />
    {% endfor %}
  </ItemGroup>
</Project>
```

### Custom Program.cs Template

Create `config/program.cs.template`:

```csharp
{{ using_statements }}

namespace SnippetValidator
{
    public class Validator
    {
        public static void ValidateSnippet()
        {
            {{ snippet_code }}
        }
    }
}
```

---

## Logging Configuration

### Log Format

Customize log format:

```python
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
```

### Console Colors

Define color scheme:

```python
COLORS = {
    "DEBUG": "\033[36m",    # Cyan
    "INFO": "\033[32m",     # Green
    "WARN": "\033[33m",     # Yellow
    "ERROR": "\033[31m",    # Red
    "RESET": "\033[0m"
}
```

### File Rotation

Configure log rotation:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/example-reviewer.log",
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
```

---

## Performance Tuning

### Database

```bash
# Use WAL mode for better concurrency
export DATABASE_URL="sqlite:///data/snippets.db?journal_mode=WAL"

# Increase timeout
export DATABASE_TIMEOUT="60"
```

### Compilation

```bash
# Parallel builds (experimental)
export COMPILATION_PARALLEL="true"
export COMPILATION_MAX_WORKERS="4"

# Increase timeout for slow builds
export COMPILATION_TIMEOUT="120"
```

### Ollama

```bash
# Increase timeout for large prompts
export OLLAMA_TIMEOUT="120"

# Retry failed requests
export OLLAMA_MAX_RETRIES="3"
```

---

## Security Configuration

### File Permissions

```bash
# Restrict database permissions
chmod 600 data/snippets.db

# Restrict log directory
chmod 700 logs/
```

### Workspace Isolation

```bash
# Use temporary directory
export WORKSPACE_BASE_PATH="/tmp/example-reviewer-workspaces"

# Auto-cleanup
export WORKSPACE_CLEANUP_AUTO="true"
```

### Network Restrictions

```bash
# Bind Ollama to localhost only
export OLLAMA_URL="http://127.0.0.1:11434"

# Disable network in compiled code (firewall rules)
# iptables -A OUTPUT -m owner --uid-owner reviewer -j REJECT
```

---

## Docker Configuration

### Environment File

Create `.env`:

```env
DATABASE_PATH=/data/snippets.db
CONTENT_ROOT=/content
WORKSPACE_BASE_PATH=/tmp/workspaces
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1
LOG_LEVEL=INFO
```

### Docker Compose

```yaml
version: '3.8'

services:
  example-reviewer:
    build: .
    env_file: .env
    volumes:
      - ./data:/data
      - ./content:/content
      - ./logs:/logs
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama

volumes:
  ollama-data:
```

---

## Configuration Validation

### Validation Script

```python
import os
from pathlib import Path

def validate_config():
    errors = []

    # Check database path
    db_path = Path(os.getenv("DATABASE_PATH", "data/snippets.db"))
    if not db_path.parent.exists():
        errors.append(f"Database directory does not exist: {db_path.parent}")

    # Check content root
    content_root = Path(os.getenv("CONTENT_ROOT", "../../content"))
    if not content_root.exists():
        errors.append(f"Content root does not exist: {content_root}")

    # Check Ollama connectivity
    import requests
    try:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        requests.get(f"{ollama_url}/api/tags", timeout=5)
    except Exception as e:
        errors.append(f"Cannot connect to Ollama: {e}")

    return errors

errors = validate_config()
if errors:
    for error in errors:
        print(f"ERROR: {error}")
    exit(1)
```

---

## Configuration Examples

### Development

```bash
# Development settings
export DATABASE_PATH="data/dev.db"
export LOG_LEVEL="DEBUG"
export WORKSPACE_CLEANUP_AUTO="false"
export OLLAMA_MODEL="llama3.1"
```

### Production

```bash
# Production settings
export DATABASE_PATH="/var/lib/example-reviewer/prod.db"
export LOG_LEVEL="INFO"
export WORKSPACE_CLEANUP_AUTO="true"
export WORKSPACE_BASE_PATH="/tmp/example-reviewer"
export OLLAMA_TIMEOUT="60"
```

### CI/CD

```bash
# CI settings
export DATABASE_PATH=":memory:"  # In-memory database
export CONTENT_ROOT="/workspace/content"
export LOG_LEVEL="WARN"
export OLLAMA_URL="http://ollama-service:11434"
```

---

## Migration Guide

### Upgrading Configuration

When upgrading, check for:

1. **New environment variables**: Review changelog
2. **Deprecated settings**: Update configuration files
3. **Schema changes**: Run database migrations

### Example Migration

```bash
# Backup old configuration
cp config/settings.json config/settings.json.backup

# Update settings
# (manually edit config/settings.json)

# Validate new configuration
python scripts/validate_config.py

# If valid, proceed
python src/cli.py discover --family zip
```

---

## Troubleshooting

### Configuration Not Loading

Check configuration hierarchy:

```python
import os
import json

print("Environment Variables:")
print(f"DATABASE_PATH: {os.getenv('DATABASE_PATH', 'NOT SET')}")

print("\nConfiguration File:")
with open("config/settings.json") as f:
    config = json.load(f)
    print(json.dumps(config, indent=2))
```

### Ollama Connection Issues

Test Ollama connectivity:

```bash
curl http://localhost:11434/api/tags
```

If fails:
1. Check Ollama is running
2. Verify firewall rules
3. Check `OLLAMA_URL` environment variable

### Database Locked

SQLite lock timeout:

```bash
export DATABASE_TIMEOUT="60"  # Increase timeout
```

Or use WAL mode:

```bash
sqlite3 data/snippets.db "PRAGMA journal_mode=WAL;"
```
