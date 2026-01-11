# Testing Guide

## Overview

This guide covers testing strategies, writing tests, and running the test suite for the Example Reviewer system.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── test_database.py           # Database ORM tests
├── test_discovery_service.py  # Discovery tests
├── test_page_scanner.py       # Markdown parsing tests
├── test_snippet_locator.py    # Locator creation tests
├── test_validation_orchestrator.py  # Validation tests
├── test_workspace_manager.py  # Workspace tests
├── test_pattern_registry.py   # Pattern matching tests
├── test_patching_service.py   # Patching tests
└── integration/               # Integration tests
    ├── test_full_pipeline.py
    └── test_database_integration.py
```

---

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_discovery_service.py
```

### Run Specific Test

```bash
pytest tests/test_discovery_service.py::test_discover_snippets
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Only Failed Tests

```bash
pytest --lf
```

### Run Tests in Parallel

```bash
pip install pytest-xdist
pytest -n 4  # Use 4 workers
```

---

## Writing Tests

### Test Naming Convention

```python
# File: tests/test_my_module.py
# Test functions: test_<functionality>

def test_create_locator():
    """Test SnippetLocator.create_locator()."""
    pass

def test_create_locator_with_empty_context():
    """Test locator creation with empty heading context."""
    pass

def test_create_locator_raises_value_error():
    """Test that invalid input raises ValueError."""
    pass
```

### Arrange-Act-Assert Pattern

```python
def test_patch_snippet():
    # Arrange: Setup test data
    snippet = create_test_snippet()
    page = create_test_page()
    service = PatchingService("test-content", db)

    # Act: Execute the function
    result = service.patch_snippet(snippet, page)

    # Assert: Verify the outcome
    assert result.success
    assert result.snippet_id == snippet.snippet_id
```

---

## Unit Tests

### Testing Database Models

```python
# tests/test_database.py
import pytest
from datetime import datetime
from src.database import Database, Snippet, Page

@pytest.fixture
def db():
    """Create in-memory database for testing."""
    db = Database(":memory:")
    db.init_schema()
    yield db

def test_create_page(db):
    """Test Page creation."""
    with db.get_session() as session:
        page = Page(
            relative_path="content/blog/example.md",
            family="zip",
            discovered_at=datetime.now(),
            last_scanned=datetime.now()
        )
        session.add(page)
        session.commit()

        assert page.page_id is not None
        assert page.family == "zip"

def test_create_snippet(db):
    """Test Snippet creation."""
    with db.get_session() as session:
        # Create page first
        page = Page(
            relative_path="test.md",
            family="zip",
            discovered_at=datetime.now(),
            last_scanned=datetime.now()
        )
        session.add(page)
        session.flush()

        # Create snippet
        snippet = Snippet(
            page_id=page.page_id,
            original_code="var x = 1;",
            locator_json='{}',
            status='discovered',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(snippet)
        session.commit()

        assert snippet.snippet_id is not None
        assert snippet.page.relative_path == "test.md"
```

### Testing Snippet Locator

```python
# tests/test_snippet_locator.py
import pytest
import json
from src.snippet_locator import SnippetLocator

def test_create_locator():
    """Test locator creation with valid input."""
    locator = SnippetLocator.create_locator(
        snippet_code="var x = 1;",
        file_path="content/blog/example.md",
        heading_context=["Installation", "NuGet"],
        snippet_ordinal=2
    )

    assert "snippet_content_hash" in locator
    assert locator["heading_context"] == ["Installation", "NuGet"]
    assert locator["snippet_ordinal"] == 2
    assert locator["file_relative_path"] == "content/blog/example.md"

def test_locator_hash_consistency():
    """Test that same code produces same hash."""
    code = "var x = 1;"

    locator1 = SnippetLocator.create_locator(code, "a.md", [], 1)
    locator2 = SnippetLocator.create_locator(code, "b.md", [], 2)

    assert locator1["snippet_content_hash"] == locator2["snippet_content_hash"]

def test_locator_hash_uniqueness():
    """Test that different code produces different hash."""
    locator1 = SnippetLocator.create_locator("var x = 1;", "a.md", [], 1)
    locator2 = SnippetLocator.create_locator("var y = 2;", "a.md", [], 1)

    assert locator1["snippet_content_hash"] != locator2["snippet_content_hash"]
```

### Testing Pattern Registry

```python
# tests/test_pattern_registry.py
import pytest
import re
from src.pattern_registry import PatternRegistry, PatternFix

def test_get_pattern_fixes_zip():
    """Test getting ZIP pattern fixes."""
    fixes = PatternRegistry.get_pattern_fixes("zip")

    assert len(fixes) > 0
    assert all(isinstance(f, PatternFix) for f in fixes)

def test_pattern_fix_matching():
    """Test pattern fix regex matching."""
    fix = PatternFix(
        name="Test Fix",
        error_pattern=r"CS0246.*'Archive'",
        old_pattern=r"^",
        new_pattern="using Aspose.Zip;\n",
        description="Test"
    )

    error = "CS0246: The type or namespace name 'Archive' could not be found"
    assert re.search(fix.error_pattern, error)

def test_pattern_fix_replacement():
    """Test pattern fix code replacement."""
    fix = PatternFix(
        name="Add using",
        error_pattern=r"CS0246",
        old_pattern=r"^",
        new_pattern="using Aspose.Zip;\n",
        description="Add using directive"
    )

    original = "var x = new Archive();"
    fixed = re.sub(fix.old_pattern, fix.new_pattern, original, count=1)

    assert fixed == "using Aspose.Zip;\nvar x = new Archive();"
```

### Testing Page Scanner

```python
# tests/test_page_scanner.py
import pytest
from pathlib import Path
from src.page_scanner import PageScanner

@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file."""
    content = '''# Example

## Installation

```bash
npm install
```

## Usage

```csharp
using Aspose.Zip;
var archive = new Archive();
```

More text here.

```csharp
archive.Save("output.zip");
```
'''
    file_path = tmp_path / "example.md"
    file_path.write_text(content)
    return file_path

def test_scan_file(sample_markdown, tmp_path):
    """Test scanning markdown file for snippets."""
    result = PageScanner.scan_file(str(sample_markdown), str(tmp_path), "zip")

    assert result.relative_path == "example.md"
    assert result.family == "zip"
    assert len(result.snippets) == 2  # Only C# snippets

    # First snippet
    assert "using Aspose.Zip" in result.snippets[0]['code']
    assert result.snippets[0]['language'] == "csharp"
    assert result.snippets[0]['heading_context'] == ["Example", "Usage"]
    assert result.snippets[0]['ordinal'] == 1

    # Second snippet
    assert "archive.Save" in result.snippets[1]['code']
    assert result.snippets[1]['ordinal'] == 2

def test_scan_file_no_snippets(tmp_path):
    """Test scanning file with no code snippets."""
    file_path = tmp_path / "no_code.md"
    file_path.write_text("# Just text\n\nNo code here.")

    result = PageScanner.scan_file(str(file_path), str(tmp_path), "zip")

    assert len(result.snippets) == 0
```

---

## Integration Tests

### Testing Discovery Service

```python
# tests/integration/test_discovery_integration.py
import pytest
from pathlib import Path
from src.database import Database, Page, Snippet
from src.discovery_service import DiscoveryService

@pytest.fixture
def test_content_dir(tmp_path):
    """Create test content directory."""
    content_dir = tmp_path / "content" / "blog.aspose.net" / "zip"
    content_dir.mkdir(parents=True)

    # Create sample markdown file
    (content_dir / "example.md").write_text('''
# Example

```csharp
var x = 1;
```
''')

    return tmp_path / "content"

@pytest.fixture
def test_db():
    """Create test database."""
    db = Database(":memory:")
    db.init_schema()
    yield db

def test_discover_snippets_integration(test_content_dir, test_db):
    """Test full discovery pipeline."""
    service = DiscoveryService(str(test_content_dir), test_db)
    result = service.discover_snippets("zip")

    assert result.total_snippets == 1
    assert result.total_pages == 1

    # Verify database state
    with test_db.get_session() as session:
        pages = session.query(Page).all()
        assert len(pages) == 1
        assert pages[0].family == "zip"

        snippets = session.query(Snippet).all()
        assert len(snippets) == 1
        assert "var x = 1;" in snippets[0].original_code
```

### Testing Workspace Manager

```python
# tests/test_workspace_manager.py
import pytest
from pathlib import Path
from src.workspace_manager import WorkspaceManager

@pytest.fixture
def workspace_mgr(tmp_path):
    """Create workspace manager with temp base path."""
    return WorkspaceManager(str(tmp_path / "workspaces"))

def test_create_workspace(workspace_mgr):
    """Test workspace creation."""
    snippet_code = "var x = 1;"
    workspace_path = workspace_mgr.create_workspace(123, snippet_code)

    assert Path(workspace_path).exists()
    assert Path(workspace_path, "Program.cs").exists()
    assert Path(workspace_path, "Validator.csproj").exists()

def test_compile_valid_code(workspace_mgr):
    """Test compiling valid C# code."""
    snippet_code = "var x = 1;"
    workspace_path = workspace_mgr.create_workspace(124, snippet_code)

    result = workspace_mgr.compile(workspace_path)

    assert result.success
    assert result.compilation_time > 0

def test_compile_invalid_code(workspace_mgr):
    """Test compiling invalid C# code."""
    snippet_code = "invalid syntax here!!!"
    workspace_path = workspace_mgr.create_workspace(125, snippet_code)

    result = workspace_mgr.compile(workspace_path)

    assert not result.success
    assert "error CS" in result.error_messages

def test_cleanup_workspace(workspace_mgr):
    """Test workspace cleanup."""
    snippet_code = "var x = 1;"
    workspace_path = workspace_mgr.create_workspace(126, snippet_code)

    assert Path(workspace_path).exists()

    workspace_mgr.cleanup(workspace_path)

    assert not Path(workspace_path).exists()
```

### Testing Full Pipeline

```python
# tests/integration/test_full_pipeline.py
import pytest
from pathlib import Path
from src.database import Database
from src.discovery_service import DiscoveryService
from src.validation_orchestrator import ValidationOrchestrator
from src.workspace_manager import WorkspaceManager
from src.pattern_registry import PatternRegistry

@pytest.fixture
def test_setup(tmp_path):
    """Setup test environment with database and content."""
    # Create content
    content_dir = tmp_path / "content" / "blog.aspose.net" / "zip"
    content_dir.mkdir(parents=True)

    (content_dir / "example.md").write_text('''
# Example

```csharp
using Aspose.Zip;
var archive = new Archive();
```
''')

    # Create database
    db = Database(":memory:")
    db.init_schema()

    # Create workspace manager
    workspace_mgr = WorkspaceManager(str(tmp_path / "workspaces"))

    return {
        'content_dir': content_dir.parent.parent.parent,
        'db': db,
        'workspace_mgr': workspace_mgr
    }

def test_full_pipeline(test_setup):
    """Test discovery → validation pipeline."""
    # 1. Discovery
    discovery = DiscoveryService(str(test_setup['content_dir']), test_setup['db'])
    result = discovery.discover_snippets("zip")

    assert result.total_snippets == 1

    # 2. Validation
    pattern_reg = PatternRegistry()
    validator = ValidationOrchestrator(
        test_setup['db'],
        test_setup['workspace_mgr'],
        pattern_reg
    )

    run = validator.run_validation("zip")

    assert run.total_snippets == 1
    assert run.verified_count == 1  # Should compile successfully
```

---

## Mocking and Fixtures

### Mocking Ollama

```python
# tests/test_ollama_integration.py
import pytest
from unittest.mock import Mock, patch
from src.ollama_integration import OllamaClient

@patch('requests.post')
def test_fix_code_success(mock_post):
    """Test successful Ollama code fix."""
    # Mock response
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        'response': 'var x = new Archive();'
    }

    client = OllamaClient()
    fixed = client.fix_code(
        original_code="var x = Archive();",
        error_messages="CS0246: Missing 'new' keyword",
        pattern_fixes=[]
    )

    assert "new Archive()" in fixed
    assert mock_post.called

@patch('requests.post')
def test_fix_code_timeout(mock_post):
    """Test Ollama timeout handling."""
    import requests
    mock_post.side_effect = requests.Timeout()

    client = OllamaClient()

    with pytest.raises(OllamaError):
        client.fix_code("var x = 1;", "error", [])
```

### Shared Fixtures

```python
# tests/conftest.py
import pytest
from datetime import datetime
from pathlib import Path
from src.database import Database, Page, Snippet

@pytest.fixture
def db():
    """In-memory database."""
    db = Database(":memory:")
    db.init_schema()
    yield db

@pytest.fixture
def sample_page(db):
    """Create a sample page."""
    with db.get_session() as session:
        page = Page(
            relative_path="content/blog/example.md",
            family="zip",
            discovered_at=datetime.now(),
            last_scanned=datetime.now()
        )
        session.add(page)
        session.commit()
        yield page

@pytest.fixture
def sample_snippet(db, sample_page):
    """Create a sample snippet."""
    with db.get_session() as session:
        snippet = Snippet(
            page_id=sample_page.page_id,
            original_code="var x = 1;",
            locator_json='{"snippet_content_hash": "abc123"}',
            status='discovered',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(snippet)
        session.commit()
        yield snippet

@pytest.fixture
def temp_content_dir(tmp_path):
    """Create temporary content directory."""
    content = tmp_path / "content" / "blog.aspose.net" / "zip"
    content.mkdir(parents=True)
    yield content
```

---

## Test Coverage

### Measuring Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

### Coverage Goals

- **Overall**: > 80%
- **Critical modules** (database, patching): > 90%
- **Utility modules**: > 70%

### Viewing Coverage Report

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Excluding Files from Coverage

`.coveragerc`:

```ini
[run]
omit =
    */tests/*
    */migrations/*
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## Performance Tests

### Benchmarking

```python
# tests/test_performance.py
import pytest
import time
from src.discovery_service import DiscoveryService

def test_discovery_performance(test_db, test_content_dir):
    """Test discovery performance."""
    service = DiscoveryService(str(test_content_dir), test_db)

    start = time.time()
    result = service.discover_snippets("zip")
    duration = time.time() - start

    # Should process 100 files in under 5 seconds
    assert duration < 5.0
    assert result.total_snippets > 0

@pytest.mark.slow
def test_validation_performance(test_db, workspace_mgr):
    """Test validation performance (marked as slow)."""
    # ... performance test that takes longer
    pass
```

Run performance tests:

```bash
pytest -m slow  # Run only slow tests
pytest -m "not slow"  # Skip slow tests
```

---

## Continuous Integration

### GitHub Actions

`.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.8', '3.9', '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
        fail_ci_if_error: true
```

---

## Test Best Practices

### 1. Test Independence

Each test should be independent:

```python
# GOOD: Uses fixture
def test_create_snippet(db):
    # Fresh database per test
    pass

# BAD: Depends on previous test
def test_query_snippet():
    # Assumes test_create_snippet ran first
    pass
```

### 2. Clear Test Names

```python
# GOOD
def test_patch_snippet_with_verified_code_succeeds():
    pass

# BAD
def test_patch():
    pass
```

### 3. One Assertion Per Test

```python
# GOOD
def test_snippet_has_correct_status():
    assert snippet.status == 'verified'

def test_snippet_has_verified_code():
    assert snippet.verified_code is not None

# ACCEPTABLE (related assertions)
def test_snippet_creation():
    assert snippet.snippet_id is not None
    assert snippet.created_at is not None
```

### 4. Use Parametrize for Multiple Cases

```python
@pytest.mark.parametrize("code,expected_hash", [
    ("var x = 1;", "abc123..."),
    ("var y = 2;", "def456..."),
])
def test_hash_calculation(code, expected_hash):
    locator = SnippetLocator.create_locator(code, "a.md", [], 1)
    assert locator["snippet_content_hash"] == expected_hash
```

---

## Debugging Tests

### Print Debugging

```python
def test_my_function():
    result = my_function()
    print(f"Result: {result}")  # Use -s flag to see output
    assert result == expected
```

Run with output:

```bash
pytest -s tests/test_my_module.py
```

### Using pdb

```python
def test_my_function():
    result = my_function()
    import pdb; pdb.set_trace()  # Debugger will pause here
    assert result == expected
```

### pytest fixtures debugging

```bash
pytest --fixtures  # List all available fixtures
pytest --setup-show  # Show fixture setup/teardown
```

---

## Running Specific Test Categories

### Mark Tests

```python
@pytest.mark.slow
def test_long_running_operation():
    pass

@pytest.mark.integration
def test_full_pipeline():
    pass

@pytest.mark.unit
def test_simple_function():
    pass
```

### Run by Mark

```bash
pytest -m slow           # Run only slow tests
pytest -m "not slow"     # Skip slow tests
pytest -m integration    # Run only integration tests
pytest -m "unit or integration"  # Run unit OR integration
```

---

## Test Maintenance

### Update Tests When Code Changes

When changing code:
1. Update affected tests
2. Add new tests for new functionality
3. Remove obsolete tests

### Refactor Tests

Apply DRY principle to tests:

```python
# Before: Repeated setup
def test_a():
    db = Database(":memory:")
    db.init_schema()
    # ... test logic

def test_b():
    db = Database(":memory:")
    db.init_schema()
    # ... test logic

# After: Using fixture
@pytest.fixture
def db():
    db = Database(":memory:")
    db.init_schema()
    yield db

def test_a(db):
    # ... test logic

def test_b(db):
    # ... test logic
```
