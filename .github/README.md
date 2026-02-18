# .github/ - GitHub Configuration

## Workflows

- `workflows/cli_tests.yml` - CI pipeline with two jobs:
  - **Static Import Analysis** - Runs `analyze_cli_imports.py` on core modules
  - **Unit Tests** - Runs `pytest tests/` with 120s timeout
