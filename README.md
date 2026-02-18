# Example Reviewer

Automated VFV (Verify-Fix-Verify) pipeline that extracts C# code examples from Aspose markdown blog posts, compiles and runs them against real NuGet packages, auto-fixes failures using deterministic patterns and LLM, then commits verified corrections back to the markdown.

## Prerequisites

- **Python 3.10+**
- **.NET 8.0 SDK** (`dotnet --version`)
- **Aspose NuGet license** (trial works for most families)
- **LLM endpoint** (OpenAI-compatible API for code fixing)

## Quick Setup

```bash
git clone <repo-url>
cd example-reviewer

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for testing

# Restore .NET packages
dotnet restore test-examples/AsposeZipValidator.csproj

# Configure LLM endpoint in config/global.json
# Configure family in config/families/<family>.json
```

## Running the Pipeline

```bash
# Run full VFV pipeline for a family
python -m src.cli.main run --family zip

# Discover examples only
python -m src.cli.main discover --family zip

# Check pipeline status
python -m src.cli.main status --family zip

# List configured families
python -m src.cli.main list-families
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `src/` | Core pipeline source code (CLI, orchestrator, services) |
| `scripts/` | Setup, operations, validation, and pattern management scripts |
| `tests/` | Unit tests (639 tests) and test fixtures |
| `config/` | Global and per-family configuration (JSON) |
| `test-examples/` | .NET project for C# compilation |
| `migrations/` | Database upgrade scripts (auto-applied; fresh installs need none) |
| `docs/` | Full documentation |
| `archive/` | Historical files preserved for git history |

Each directory contains its own `README.md` with details about its contents.

## Configuration

### Global Config (`config/global.json`)

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-oss",
    "base_url": "https://your-endpoint/v1",
    "api_key_env_var": "YOUR_API_KEY_ENV_VAR"
  },
  "database": {
    "path": "./data/example_reviewer.db"
  }
}
```

### Family Config (`config/families/<family>.json`)

Each Aspose product family (zip, words, email, etc.) has its own config specifying:
- Content root directories (where markdown files live)
- NuGet package and version
- API catalog path (generated via assembly reflection)
- Safe using directives

### Generating an API Catalog

```bash
python scripts/setup/extract_assembly_catalog.py Aspose.ZIP 25.1.0 Aspose.Zip --full \
  > config/families/zip_api_catalog.json
```

## How It Works

1. **Discover** - Scan markdown files for fenced C# code blocks
2. **Compile** - Extract code, wrap in Main(), compile via `dotnet build`
3. **Fix (Deterministic)** - Apply 10+ deterministic fix patterns (using directives, stream disposal, enum corrections)
4. **Fix (LLM)** - Send remaining errors to LLM with API catalog context
5. **Verify** - Run compiled code, validate output
6. **Review** - LLM reviews changes for semantic drift
7. **Commit** - Update markdown files with verified code

## Running Tests

```bash
pytest tests/ -v --timeout=120
```

## Documentation

See [docs/](docs/) for full documentation:
- [Pipeline Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Configuration Reference](docs/configuration.md)
- [Operations Runbook](docs/ops-runbook.md)
