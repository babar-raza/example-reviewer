# LLM Exploration Guide

This package contains a comprehensive snapshot of the **Aspose.ZIP Example Reviewer** project for LLM exploration and analysis.

## Package Contents

### 1. Source Code (`src/`)
Complete Python source code organized by functionality:

- **`cli.py`** - Command-line interface with all commands (discover, validate, patch)
- **`core/`** - Core infrastructure
  - `database.py` - SQLite database operations and schema management
  - `config_utils.py` - Configuration loading and family management
  - `telemetry.py` - Metrics collection and reporting
- **`discovery/`** - Content discovery and snippet extraction
  - `discovery_service.py` - Main discovery orchestration
  - `gist_service.py` - GitHub Gist integration
  - `page_scanner.py` - Web page scanning and parsing
  - `snippet_locator.py` - Code snippet extraction from markdown
- **`validation/`** - Code validation and compilation
  - `orchestrator.py` - Validation pipeline orchestration
  - `analysis/` - Code analysis and pattern detection
  - `fixing/` - Automated fix application
  - `workspace/` - .NET workspace management
- **`patching/`** - Content patching and publishing
  - `patching_service.py` - Patch generation and application
  - `gist_publisher.py` - GitHub Gist publishing
  - `placeholder_patcher.py` - Placeholder replacement
- **`api_reference/`** - API reference indexing
- **`llm/`** - LLM integration (Ollama)
- **`legacy/`** - Deprecated code (for reference)

### 2. Documentation (`docs/`)
User-facing documentation:

- **`architecture.md`** - System design and component overview
- **`configuration.md`** - Environment setup and configuration
- **`development-guide.md`** - Contributing and development workflow
- **`testing-guide.md`** - Test suite and testing practices
- **`api-reference.md`** - Code API documentation
- **`troubleshooting.md`** - Common issues and solutions
- **`operations.md`** - Cache/database management
- **`security.md`** - GitHub token and security practices
- **`performance.md`** - Performance optimization
- **`patching-strategies.md`** - Patching workflow details

### 3. Technical Specifications (`specs/`)
Technical design documents:

- **`architecture.md`** - Architecture design
- **`database-schema.md`** - Database structure
- **`family_config_schema.md`** - Family configuration format
- **`patching-strategies.md`** - Patching strategy details
- **`api-reference.md`** - API reference specifications

### 4. Tests (`tests/`)
Comprehensive test suite with pytest:

- Integration tests for all major features
- Gist handling tests
- Runtime validation tests
- Telemetry tests
- Test fixtures in `fixtures/`

### 5. Configuration (`config/`)
Product family configurations:

- **`families/*.json`** - Family-specific settings (zip, pdf, cells, words, etc.)
- **`global.json`** - Global configuration

### 6. Implementation Plans (`plans/`)
Active and historical implementation plans:

- **`runtime_validation_plan.md`** - Runtime validation design
- **`runtime_code_healing.md`** - Code healing implementation
- **`healing/`** - Auto-commit and telemetry fixes
- **`from_chat/`** - Plans from chat sessions

### 7. Database Schema (`schema.sql`)
Complete SQLite database schema with:
- Pages, snippets, validation results
- Execution results and runtime validation
- API reference index
- Namespace mappings
- Dependency resolution

### 8. Root Documentation
Key project documents:
- **`README.md`** - Project overview and quick start
- **`QUICKSTART.md`** - Quick start guide
- **`EXECUTIVE_SUMMARY.md`** - High-level project summary
- **`IMPLEMENTATION-PLAN.md`** - Overall implementation plan
- **`PHASE5_IMPLEMENTATION.md`** - Phase 5 details
- **`API_REFERENCE_ENHANCEMENT_RESULTS.md`** - API reference enhancement results
- **`MULTI_FAMILY_VERIFICATION_RESULTS.md`** - Multi-family testing results
- **`VALIDATION_FAILURE_ANALYSIS.md`** - Validation failure analysis

### 9. Configuration Files
- **`requirements.txt`** - Python dependencies
- **`requirements-dev.txt`** - Development dependencies
- **`pytest.ini`** - Pytest configuration
- **`.env.example`** - Environment variable template
- **`.gitignore`** - Git ignore patterns

### 10. Entry Points
- **`run.py`** - Simple run script
- **`run_cli.py`** - CLI entry point
- **`run_tests.py`** - Test runner
- **`run_validation.py`** - Validation runner

## Project Purpose

The **Aspose.ZIP Example Reviewer** is a systematic tool to:
1. **Discover** - Scan Aspose.NET documentation sites for code examples
2. **Validate** - Compile and execute examples against the latest NuGet packages
3. **Fix** - Automatically detect and fix common issues and AI hallucinations
4. **Patch** - Apply verified fixes back to documentation

## Key Features

### Code Issue Detection
- DeflateCompressionSettings constructor hallucinations
- SaveAsync/async method hallucinations
- Stream disposal timing issues
- Missing using statements and namespaces
- Incorrect API usage patterns

### Validation Pipeline
1. **Discovery** - Extract snippets from markdown content
2. **Compilation** - Validate C# code against Aspose.ZIP NuGet
3. **Runtime** - Execute code with test data to verify behavior
4. **Analysis** - Pattern detection and issue classification
5. **Fixing** - Apply automated fixes and track results
6. **Patching** - Publish fixes back to Gists or content files

### Multi-Family Support
Configured for multiple Aspose product families:
- Aspose.ZIP
- Aspose.PDF
- Aspose.Cells
- Aspose.Words
- Aspose.Slides
- Aspose.Email
- Aspose.Imaging

## Database Schema Highlights

**Key Tables:**
- `pages` - Discovered web pages
- `snippets` - Extracted code snippets
- `validation_results` - Compilation results
- `execution_results` - Runtime validation results
- `fixes` - Applied fixes and their status
- `api_reference` - API method index
- `namespace_mappings` - API to namespace mappings

## Technology Stack

- **Python 3.8+** - Core application
- **.NET 8.0 SDK** - C# compilation and execution
- **SQLite** - Database storage
- **pytest** - Testing framework
- **requests** - HTTP client
- **BeautifulSoup** - HTML parsing (legacy)
- **regex** - Advanced pattern matching
- **PyYAML** - Configuration parsing

## Usage Workflow

```bash
# 1. Discover snippets
python -m src.cli discover --family zip

# 2. Validate snippets
python -m src.cli validate --family zip

# 3. Patch fixes back to content
python -m src.cli patch --family zip --dry-run
```

## Statistics (as of last run)

- **172 pages** scanned (Aspose.ZIP family)
- **13 examples** in sample review
- **Common issues**: DeflateCompressionSettings params (6), SaveAsync (1), manual directory iteration (3)
- **Fix success rate**: High for pattern-based fixes

## What's NOT Included

To keep the package focused, the following are excluded:
- Virtual environments (`venv/`)
- Python cache files (`__pycache__/`, `*.pyc`)
- Git repository (`.git/`)
- Runtime artifacts (`artifacts/`, `logs/`, `cache/`)
- Test data files (`test-data/`)
- Compiled .NET workspaces (`workspaces/`)
- External dependencies source
- Coverage reports (`.coverage`)

## Exploring the Codebase

### Start Here:
1. **`README.md`** - Project overview
2. **`docs/architecture.md`** - Understand system design
3. **`src/cli.py`** - See available commands
4. **`schema.sql`** - Database structure

### Key Code Paths:
- **Discovery**: `src/discovery/discovery_service.py` → `page_scanner.py` → `snippet_locator.py`
- **Validation**: `src/validation/orchestrator.py` → `workspace_manager.py`
- **Patching**: `src/patching/patching_service.py` → `gist_publisher.py`

### Testing:
- Start with `tests/README.md`
- Check `tests/test_gist_integration.py` for end-to-end examples

## Questions to Explore

1. How does the discovery pipeline work?
2. What validation strategies are used?
3. How are fixes tracked and applied?
4. What patterns are detected?
5. How does the runtime validation work?
6. How are multiple product families configured?
7. What telemetry is collected?
8. How is the API reference indexed?

## Version Information

- **Project**: Aspose.ZIP Example Reviewer
- **Python**: 3.8+
- **.NET**: 8.0
- **Aspose.ZIP**: 25.12.0 (latest validated)
- **Database Schema**: Version 6 (with dependency resolution)

---

**Note**: This is a snapshot for exploration. For the latest code, refer to the original repository.
