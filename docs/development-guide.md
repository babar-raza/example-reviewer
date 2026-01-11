# Development Guide

## Getting Started

### Prerequisites

- Python 3.8+
- .NET SDK 8.0+
- Git
- Ollama (for AI-powered fixing)
- SQLite3

### Setup Development Environment

```bash
# Clone repository
cd d:/onedrive/Documents/GitHub/aspose.net/scripts/example-reviewer

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black mypy pylint

# Initialize database
python src/cli.py discover --family zip

# Verify installation
python -m pytest tests/
```

### Directory Structure

```
example-reviewer/
├── .venv/                  # Python virtual environment
├── config/                 # Configuration files
├── data/                   # SQLite database
│   └── snippets.db
├── docs/                   # Documentation
│   ├── development-guide.md
│   ├── troubleshooting.md
│   └── ...
├── logs/                   # Application logs
├── specs/                  # Technical specifications
│   ├── architecture.md
│   ├── database-schema.md
│   └── ...
├── src/                    # Source code
│   ├── cli.py             # Entry point
│   ├── database.py        # ORM models
│   ├── discovery_service.py
│   ├── validation_orchestrator.py
│   ├── patching_service.py
│   └── ...
├── test-examples/          # Test .NET project
│   ├── Program.cs
│   └── Validator.csproj
├── tests/                  # Unit and integration tests
├── workspaces/            # Temporary compilation directories
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/add-pdf-support
```

### 2. Write Code

Follow coding standards (see below).

### 3. Write Tests

Create test file in `tests/`:

```python
# tests/test_my_feature.py
import pytest
from src.my_module import MyClass

def test_my_feature():
    obj = MyClass()
    result = obj.my_method("input")
    assert result == "expected"
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/test_my_feature.py::test_my_function
```

### 5. Format Code

```bash
# Format with black
black src/ tests/

# Check types
mypy src/

# Lint
pylint src/
```

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add PDF support

- Add PDF family configuration
- Implement PDF-specific pattern fixes
- Add tests for PDF validation"
```

### 7. Push and Create PR

```bash
git push origin feature/add-pdf-support
```

---

## Coding Standards

### Python Style

Follow PEP 8 with these conventions:

```python
# Imports
import os
import sys
from pathlib import Path
from typing import List, Optional

from database import Database, Snippet
from discovery_service import DiscoveryService

# Constants
MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Class names: PascalCase
class ValidationOrchestrator:
    def __init__(self, db: Database):
        self.db = db

    # Method names: snake_case
    def run_validation(self, family: str) -> ValidationRun:
        """
        Run validation for a product family.

        Args:
            family: Product family name

        Returns:
            ValidationRun instance with results
        """
        pass

# Function names: snake_case
def normalize_code(code: str) -> str:
    """Normalize code for comparison."""
    return code.strip().lower()
```

### Type Hints

Always use type hints:

```python
from typing import List, Optional, Dict, Tuple

def process_snippets(
    snippets: List[Snippet],
    max_attempts: int = 3
) -> Dict[int, bool]:
    """Process list of snippets."""
    results: Dict[int, bool] = {}
    for snippet in snippets:
        results[snippet.snippet_id] = True
    return results
```

### Documentation

Use Google-style docstrings:

```python
def patch_snippet(
    snippet: Snippet,
    page: Page,
    dry_run: bool = False
) -> PatchResult:
    """
    Patch a single snippet into its markdown file.

    Args:
        snippet: Snippet to patch
        page: Page containing the snippet
        dry_run: If True, don't modify file

    Returns:
        PatchResult with success status and metadata

    Raises:
        IOError: If file cannot be read/written
        ValueError: If snippet has no verified code

    Example:
        >>> result = patch_snippet(snippet, page)
        >>> if result.success:
        ...     print(f"Patched {result.file_path}")
    """
    pass
```

### Error Handling

```python
# Specific exceptions
try:
    snippet = session.query(Snippet).get(snippet_id)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise

# Context managers for resources
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Graceful degradation
try:
    fixed_code = ollama.fix_code(original, errors, patterns)
except OllamaError:
    logger.warning("Ollama unavailable, skipping AI fix")
    fixed_code = None
```

---

## Testing Guidelines

### Unit Tests

Test individual functions and classes in isolation:

```python
# tests/test_snippet_locator.py
import pytest
from src.snippet_locator import SnippetLocator

def test_create_locator():
    locator = SnippetLocator.create_locator(
        snippet_code="var x = 1;",
        file_path="content/blog/example.md",
        heading_context=["Installation"],
        snippet_ordinal=1
    )

    assert "snippet_content_hash" in locator
    assert locator["heading_context"] == ["Installation"]
    assert locator["snippet_ordinal"] == 1
```

### Integration Tests

Test components working together:

```python
# tests/test_integration_discovery.py
import pytest
from src.database import Database
from src.discovery_service import DiscoveryService

@pytest.fixture
def test_db():
    db = Database(":memory:")
    db.init_schema()
    yield db

def test_discovery_integration(test_db):
    service = DiscoveryService("test-content", test_db)
    result = service.discover_snippets("zip")

    assert result.total_snippets > 0

    with test_db.get_session() as session:
        snippets = session.query(Snippet).all()
        assert len(snippets) == result.total_snippets
```

### Fixtures

Create reusable test fixtures:

```python
# tests/conftest.py
import pytest
from src.database import Database, Snippet, Page

@pytest.fixture
def db():
    """In-memory database for tests."""
    db = Database(":memory:")
    db.init_schema()
    yield db

@pytest.fixture
def sample_snippet(db):
    """Create a sample snippet for testing."""
    with db.get_session() as session:
        page = Page(
            relative_path="test/example.md",
            family="zip",
            discovered_at=datetime.now(),
            last_scanned=datetime.now()
        )
        session.add(page)
        session.flush()

        snippet = Snippet(
            page_id=page.page_id,
            original_code="var x = 1;",
            locator_json='{}',
            status='discovered'
        )
        session.add(snippet)
        session.commit()

        yield snippet
```

### Mocking External Dependencies

```python
# tests/test_ollama_integration.py
from unittest.mock import Mock, patch
import pytest
from src.ollama_integration import OllamaClient

@patch('requests.post')
def test_ollama_fix_code(mock_post):
    # Mock Ollama API response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'response': 'var x = new Archive();'
    }

    client = OllamaClient()
    fixed = client.fix_code("var x = Archive();", "CS0246", [])

    assert "new Archive()" in fixed
    mock_post.assert_called_once()
```

---

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL="DEBUG"
python src/cli.py validate --family zip
```

### Interactive Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use debugger-friendly breakpoint (Python 3.7+)
breakpoint()
```

### VSCode Debug Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "CLI: Discover",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/cli.py",
      "args": ["discover", "--family", "zip"],
      "console": "integratedTerminal",
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "CLI: Validate",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/cli.py",
      "args": ["validate", "--family", "zip"],
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Database Inspection

```bash
# Open database in sqlite3
sqlite3 data/snippets.db

# Useful queries
.schema snippets
SELECT COUNT(*) FROM snippets WHERE status = 'verified';
SELECT * FROM validation_runs ORDER BY started_at DESC LIMIT 5;
```

---

## Performance Profiling

### Using cProfile

```python
import cProfile
import pstats

from src.discovery_service import DiscoveryService
from src.database import Database

db = Database()
service = DiscoveryService("../../content", db)

# Profile discovery
cProfile.run(
    'service.discover_snippets("zip")',
    'profile_stats'
)

# Analyze results
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Using line_profiler

```bash
# Install
pip install line_profiler

# Add @profile decorator to function
@profile
def my_function():
    pass

# Run profiler
kernprof -l -v src/my_module.py
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    large_list = [i for i in range(10000000)]
    return sum(large_list)
```

---

## Adding New Features

### Example: Add PDF Support

#### 1. Update Family Configuration

Edit `config/families.json`:

```json
{
  "pdf": {
    "display_name": "Aspose.PDF for .NET",
    "content_pattern": "**/pdf/**/*.md",
    "nuget_packages": [
      {"name": "Aspose.PDF", "version": "24.11.0"}
    ],
    "using_statements": [
      "using Aspose.Pdf;",
      "using Aspose.Pdf.Text;"
    ]
  }
}
```

#### 2. Add Pattern Fixes

In `pattern_registry.py`:

```python
PDF_PATTERNS = [
    PatternFix(
        name="Add using Aspose.Pdf",
        error_pattern=r"CS0246.*'Document'",
        old_pattern=r"^",
        new_pattern="using Aspose.Pdf;\n",
        description="Add PDF namespace"
    )
]

def get_pattern_fixes(family: str) -> List[PatternFix]:
    if family == "zip":
        return ZIP_PATTERNS
    elif family == "pdf":
        return PDF_PATTERNS
    return []
```

#### 3. Add Tests

Create `tests/test_pdf_support.py`:

```python
def test_pdf_discovery():
    db = Database(":memory:")
    db.init_schema()

    service = DiscoveryService("test-content", db)
    result = service.discover_snippets("pdf")

    assert result.total_snippets > 0

def test_pdf_pattern_fixes():
    fixes = PatternRegistry.get_pattern_fixes("pdf")
    assert len(fixes) > 0
```

#### 4. Test End-to-End

```bash
python src/cli.py discover --family pdf
python src/cli.py validate --family pdf
python src/cli.py patch --family pdf --dry-run
```

---

## Database Migrations

### Adding a New Column

```python
# 1. Update ORM model in database.py
class Snippet(Base):
    # ... existing columns ...
    fix_attempts = Column(Integer, default=0)

# 2. Create migration script
# migrations/add_fix_attempts_column.py
import sqlite3

def migrate():
    conn = sqlite3.connect("data/snippets.db")
    cursor = conn.cursor()

    # Add column
    cursor.execute("""
        ALTER TABLE snippets
        ADD COLUMN fix_attempts INTEGER DEFAULT 0
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()

# 3. Run migration
python migrations/add_fix_attempts_column.py
```

### Creating a New Table

```python
# 1. Add ORM model in database.py
class FixAttempt(Base):
    __tablename__ = 'fix_attempts'

    attempt_id = Column(Integer, primary_key=True)
    snippet_id = Column(Integer, ForeignKey('snippets.snippet_id'))
    strategy = Column(String)
    attempted_at = Column(DateTime)

# 2. Create table (will auto-create on next run)
db = Database()
db.init_schema()
```

---

## Continuous Integration

### GitHub Actions Example

`.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        files: ./coverage.xml
```

---

## Release Process

### Version Bumping

1. Update version in `setup.py` or `__version__.py`
2. Update CHANGELOG.md
3. Create git tag

```bash
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

### Building Distribution

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Upload to PyPI (if applicable)
twine upload dist/*
```

---

## Contributing Guidelines

### Code Review Checklist

- [ ] Code follows style guide
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Commit messages are descriptive

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed

## Checklist
- [ ] Tests pass
- [ ] Code is formatted
- [ ] Documentation updated
```

---

## Useful Commands

```bash
# Reset database
rm data/snippets.db
python src/cli.py discover --family zip

# Clean workspaces
rm -rf workspaces/*

# View logs
tail -f logs/example-reviewer.log

# Count lines of code
find src -name '*.py' | xargs wc -l

# Find TODOs
grep -r "TODO" src/

# Check database size
ls -lh data/snippets.db
```

---

## Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
