# API Reference

## Overview

This document provides detailed API documentation for all major classes and functions in the Example Reviewer system.

## Module: database.py

### Class: Database

Database connection and session management.

```python
class Database:
    def __init__(self, db_path: str = "data/snippets.db")
```

**Methods**:

#### `get_session() -> ContextManager[Session]`

Get a database session context manager.

```python
db = Database()
with db.get_session() as session:
    snippets = session.query(Snippet).all()
```

**Returns**: SQLAlchemy session context manager

#### `init_schema()`

Initialize database schema (create tables).

```python
db = Database()
db.init_schema()
```

**Side Effects**: Creates all tables if they don't exist

### Class: Page

ORM model for markdown pages.

```python
class Page(Base):
    __tablename__ = 'pages'

    page_id: int
    relative_path: str
    family: str
    discovered_at: datetime
    last_scanned: datetime
    snippet_count: int
```

**Relationships**:
- `snippets`: One-to-many with `Snippet`

### Class: Snippet

ORM model for code snippets.

```python
class Snippet(Base):
    __tablename__ = 'snippets'

    snippet_id: int
    page_id: int
    original_code: str
    verified_code: Optional[str]
    locator_json: str
    status: str  # 'discovered' | 'verified' | 'needs_fix' | 'error'
    created_at: datetime
    updated_at: datetime
```

**Relationships**:
- `page`: Many-to-one with `Page`
- `validation_results`: One-to-many with `ValidationResult`

### Class: ValidationRun

ORM model for validation execution.

```python
class ValidationRun(Base):
    __tablename__ = 'validation_runs'

    run_id: int
    family: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_snippets: int
    verified_count: int
    needs_fix_count: int
    error_count: int
```

**Relationships**:
- `results`: One-to-many with `ValidationResult`

### Class: ValidationResult

ORM model for individual validation outcomes.

```python
class ValidationResult(Base):
    __tablename__ = 'validation_results'

    result_id: int
    run_id: int
    snippet_id: int
    status: str
    compiler_output: Optional[str]
    error_messages: Optional[str]
    validated_at: datetime
    compilation_time: Optional[float]
```

**Relationships**:
- `run`: Many-to-one with `ValidationRun`
- `snippet`: Many-to-one with `Snippet`

---

## Module: discovery_service.py

### Class: DiscoveryService

Discover and extract code snippets from markdown files.

```python
class DiscoveryService:
    def __init__(self, content_root: str, db: Database)
```

**Parameters**:
- `content_root`: Path to content directory
- `db`: Database instance

#### `discover_snippets(family: str) -> DiscoveryResult`

Discover all C# snippets for a product family.

```python
service = DiscoveryService("/path/to/content", db)
result = service.discover_snippets("zip")

print(f"Found {result.total_snippets} snippets in {result.total_pages} pages")
```

**Parameters**:
- `family`: Product family name (e.g., "zip", "pdf", "words")

**Returns**: `DiscoveryResult` with summary statistics

**Side Effects**:
- Creates `Page` and `Snippet` records in database
- Updates existing pages if re-discovered

---

## Module: page_scanner.py

### Class: PageScanner

Parse markdown files and extract code snippets.

```python
class PageScanner:
    @staticmethod
    def scan_file(file_path: str, content_root: str, family: str) -> PageScanResult
```

**Parameters**:
- `file_path`: Absolute path to markdown file
- `content_root`: Root path for relative path calculation
- `family`: Product family

**Returns**: `PageScanResult` containing:
```python
@dataclass
class PageScanResult:
    relative_path: str
    family: str
    snippets: List[dict]  # List of {code, language, heading_context, ordinal}
```

**Example**:
```python
result = PageScanner.scan_file(
    "/content/blog.aspose.net/zip/example.md",
    "/content",
    "zip"
)

for snippet in result.snippets:
    print(f"Found snippet: {snippet['code'][:50]}...")
```

---

## Module: snippet_locator.py

### Class: SnippetLocator

Create locator metadata for snippets.

```python
class SnippetLocator:
    @staticmethod
    def create_locator(
        snippet_code: str,
        file_path: str,
        heading_context: List[str],
        snippet_ordinal: int
    ) -> dict
```

**Parameters**:
- `snippet_code`: Code content
- `file_path`: Relative path to file
- `heading_context`: List of headings
- `snippet_ordinal`: Position (1-indexed)

**Returns**: Locator dictionary
```python
{
    "snippet_content_hash": "sha256_hash",
    "heading_context": ["Heading 1", "Heading 2"],
    "snippet_ordinal": 1,
    "file_relative_path": "content/blog.../index.md",
    "language": "csharp"
}
```

**Example**:
```python
locator = SnippetLocator.create_locator(
    code="var x = 1;",
    file_path="content/blog.aspose.net/zip/example.md",
    heading_context=["Installation", "NuGet"],
    snippet_ordinal=2
)
```

---

## Module: validation_orchestrator.py

### Class: ValidationOrchestrator

Orchestrate validation of code snippets.

```python
class ValidationOrchestrator:
    def __init__(
        self,
        db: Database,
        workspace_manager: WorkspaceManager,
        pattern_registry: PatternRegistry
    )
```

#### `run_validation(family: str) -> ValidationRun`

Validate all discovered snippets for a family.

```python
orchestrator = ValidationOrchestrator(db, workspace_mgr, pattern_reg)
run = orchestrator.run_validation("zip")

print(f"Verified: {run.verified_count}/{run.total_snippets}")
```

**Parameters**:
- `family`: Product family to validate

**Returns**: `ValidationRun` instance with results

**Side Effects**:
- Creates workspaces
- Compiles code
- Updates snippet status
- Creates validation results

---

## Module: workspace_manager.py

### Class: WorkspaceManager

Manage isolated compilation workspaces.

```python
class WorkspaceManager:
    def __init__(self, base_path: str = "workspaces")
```

#### `create_workspace(snippet_id: int, snippet_code: str) -> str`

Create an isolated workspace for a snippet.

```python
workspace_mgr = WorkspaceManager()
workspace_path = workspace_mgr.create_workspace(123, "var x = 1;")

# Returns: "workspaces/snippet_123"
```

**Parameters**:
- `snippet_id`: Unique snippet identifier
- `snippet_code`: Code to compile

**Returns**: Path to workspace directory

**Side Effects**:
- Creates directory
- Writes Program.cs
- Writes Validator.csproj

#### `compile(workspace_path: str) -> CompilationResult`

Compile code in workspace.

```python
result = workspace_mgr.compile("workspaces/snippet_123")

if result.success:
    print("Compilation successful!")
else:
    print(f"Errors: {result.error_messages}")
```

**Returns**: `CompilationResult` with:
```python
@dataclass
class CompilationResult:
    success: bool
    output: str
    error_messages: str
    compilation_time: float
```

#### `cleanup(workspace_path: str)`

Remove workspace directory.

```python
workspace_mgr.cleanup("workspaces/snippet_123")
```

---

## Module: workspace_wrapper.py

### Class: WorkspaceWrapper

Wrap code snippets for library-mode compilation.

```python
class WorkspaceWrapper:
    @staticmethod
    def wrap_for_library(snippet_code: str) -> str
```

**Parameters**:
- `snippet_code`: Original code snippet

**Returns**: Wrapped code in class structure

**Example**:
```python
original = "var archive = new Archive();"

wrapped = WorkspaceWrapper.wrap_for_library(original)

# Returns:
# using System;
# using Aspose.Zip;
# ...
# public class SnippetValidator {
#     public static void ValidateSnippet() {
#         var archive = new Archive();
#     }
# }
```

---

## Module: pattern_registry.py

### Class: PatternRegistry

Registry of pattern-based fixes for compilation errors.

```python
class PatternRegistry:
    @staticmethod
    def get_pattern_fixes(family: str) -> List[PatternFix]
```

**Parameters**:
- `family`: Product family

**Returns**: List of `PatternFix` instances

#### Class: PatternFix

```python
@dataclass
class PatternFix:
    name: str
    error_pattern: str  # Regex to match error
    old_pattern: str    # Code pattern to find
    new_pattern: str    # Replacement pattern
    description: str
```

**Example**:
```python
patterns = PatternRegistry.get_pattern_fixes("zip")

for fix in patterns:
    if re.search(fix.error_pattern, error_message):
        code = re.sub(fix.old_pattern, fix.new_pattern, code)
```

---

## Module: example_fixer.py

### Class: ExampleFixer

Fix compilation errors using patterns and AI.

```python
class ExampleFixer:
    def __init__(
        self,
        db: Database,
        workspace_manager: WorkspaceManager,
        pattern_registry: PatternRegistry,
        ollama_client: OllamaClient
    )
```

#### `fix_snippet(snippet: Snippet, max_attempts: int = 3) -> FixResult`

Attempt to fix a failing snippet.

```python
fixer = ExampleFixer(db, workspace_mgr, pattern_reg, ollama)
result = fixer.fix_snippet(snippet, max_attempts=3)

if result.success:
    print(f"Fixed! Used strategy: {result.strategy}")
    print(f"Fixed code: {result.fixed_code}")
```

**Parameters**:
- `snippet`: Snippet to fix
- `max_attempts`: Maximum fix iterations

**Returns**: `FixResult` with:
```python
@dataclass
class FixResult:
    success: bool
    fixed_code: Optional[str]
    strategy: str  # 'pattern' | 'ollama'
    attempts: int
    error: Optional[str]
```

---

## Module: ollama_integration.py

### Class: OllamaClient

Interface to Ollama LLM for code fixing.

```python
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1")
```

#### `fix_code(original_code: str, error_messages: str, pattern_fixes: List[PatternFix]) -> str`

Request code fix from Ollama.

```python
ollama = OllamaClient()
fixed_code = ollama.fix_code(
    original_code="var x = Archive();",
    error_messages="CS0246: The type or namespace name 'Archive' could not be found",
    pattern_fixes=[]
)

# Returns: "var x = new Archive();"
```

**Parameters**:
- `original_code`: Code with errors
- `error_messages`: Compiler error messages
- `pattern_fixes`: Available pattern fixes

**Returns**: Fixed code string

**Raises**: `OllamaError` if API fails

---

## Module: patching_service.py

### Class: PatchingService

Apply verified code to original markdown files.

```python
class PatchingService:
    def __init__(self, content_root: str, db: Database)
```

#### `patch_family(family: str, dry_run: bool = False) -> PatchSummary`

Patch all verified snippets for a family.

```python
service = PatchingService("/content", db)
summary = service.patch_family("zip", dry_run=True)

print(f"Patches applied: {summary.success_count}")
print(f"Errors: {summary.error_count}")
```

**Parameters**:
- `family`: Product family
- `dry_run`: If True, don't modify files

**Returns**: `PatchSummary` with:
```python
@dataclass
class PatchSummary:
    total_snippets: int
    success_count: int
    error_count: int
    files_modified: Set[str]
    results: List[PatchResult]
```

#### `patch_snippet(snippet: Snippet, page: Page, dry_run: bool = False) -> PatchResult`

Patch a single snippet.

```python
result = service.patch_snippet(snippet, page, dry_run=False)

if result.success:
    print(f"Patched {result.file_path}")
else:
    print(f"Error: {result.error}")
```

**Returns**: `PatchResult` with:
```python
@dataclass
class PatchResult:
    snippet_id: int
    file_path: str
    success: bool
    error: str
    original_content: str
    modified_content: str
```

---

## Module: telemetry.py

### Class: Telemetry

Logging and metrics collection.

```python
class Telemetry:
    @staticmethod
    def log_discovery(family: str, pages: int, snippets: int)
```

**Example**:
```python
Telemetry.log_discovery("zip", pages=27, snippets=78)
# Logs: [DISCOVERY] family=zip pages=27 snippets=78
```

### Functions

#### `log_validation(run_id: int, verified: int, needs_fix: int, errors: int)`

Log validation summary.

#### `log_patching(family: str, success: int, errors: int, files: int)`

Log patching summary.

#### `log_error(component: str, error: str)`

Log error message.

---

## Module: cli.py

### Command Line Interface

#### `discover`

```bash
python src/cli.py discover --family zip
```

**Options**:
- `--family`: Product family (required)

#### `validate`

```bash
python src/cli.py validate --family zip [--run-id RUN_ID]
```

**Options**:
- `--family`: Product family (required)
- `--run-id`: Specific run to validate (optional)

#### `fix`

```bash
python src/cli.py fix --family zip [--snippet-id ID] [--max-attempts 3]
```

**Options**:
- `--family`: Product family (required)
- `--snippet-id`: Fix specific snippet (optional)
- `--max-attempts`: Maximum fix attempts (default: 3)

#### `patch`

```bash
python src/cli.py patch --family zip [--dry-run]
```

**Options**:
- `--family`: Product family (required)
- `--dry-run`: Preview without modifying files (optional)

---

## Data Classes

### DiscoveryResult

```python
@dataclass
class DiscoveryResult:
    family: str
    total_pages: int
    total_snippets: int
    new_snippets: int
    updated_snippets: int
```

### PageScanResult

```python
@dataclass
class PageScanResult:
    relative_path: str
    family: str
    snippets: List[dict]
```

### CompilationResult

```python
@dataclass
class CompilationResult:
    success: bool
    output: str
    error_messages: str
    compilation_time: float
```

### FixResult

```python
@dataclass
class FixResult:
    success: bool
    fixed_code: Optional[str]
    strategy: str
    attempts: int
    error: Optional[str]
```

### PatchResult

```python
@dataclass
class PatchResult:
    snippet_id: int
    file_path: str
    success: bool
    error: str
    original_content: str
    modified_content: str
```

### PatchSummary

```python
@dataclass
class PatchSummary:
    total_snippets: int
    success_count: int
    error_count: int
    files_modified: Set[str]
    results: List[PatchResult]
```

---

## Type Hints

### Common Types

```python
from typing import Optional, List, Dict, Set, Tuple

# Database session
Session = sqlalchemy.orm.Session

# File paths
FilePath = str
RelativePath = str

# Snippet status
SnippetStatus = Literal['discovered', 'verified', 'needs_fix', 'error']

# Fix strategy
FixStrategy = Literal['pattern', 'ollama']
```

---

## Exceptions

### OllamaError

Raised when Ollama API fails.

```python
try:
    fixed_code = ollama.fix_code(code, errors, patterns)
except OllamaError as e:
    print(f"Ollama API failed: {e}")
```

### DatabaseError

Raised on database operations failure.

```python
try:
    db.init_schema()
except DatabaseError as e:
    print(f"Database error: {e}")
```

### WorkspaceError

Raised when workspace operations fail.

```python
try:
    workspace_mgr.create_workspace(123, code)
except WorkspaceError as e:
    print(f"Workspace error: {e}")
```

---

## Configuration

### Environment Variables

```python
# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/snippets.db")

# Content root
CONTENT_ROOT = os.getenv("CONTENT_ROOT", "../../content")

# Ollama URL
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Ollama model
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
```

### Usage

```bash
export DATABASE_PATH="/custom/path/snippets.db"
export OLLAMA_MODEL="codellama"

python src/cli.py validate --family zip
```

---

## Example Usage

### Full Pipeline

```python
from database import Database
from discovery_service import DiscoveryService
from validation_orchestrator import ValidationOrchestrator
from patching_service import PatchingService
from workspace_manager import WorkspaceManager
from pattern_registry import PatternRegistry

# Initialize
db = Database("data/snippets.db")
db.init_schema()

# 1. Discovery
discovery = DiscoveryService("../../content", db)
result = discovery.discover_snippets("zip")
print(f"Discovered {result.total_snippets} snippets")

# 2. Validation
workspace_mgr = WorkspaceManager()
pattern_reg = PatternRegistry()
validator = ValidationOrchestrator(db, workspace_mgr, pattern_reg)
run = validator.run_validation("zip")
print(f"Verified {run.verified_count} snippets")

# 3. Patching
patcher = PatchingService("../../content", db)
summary = patcher.patch_family("zip", dry_run=False)
print(f"Patched {summary.success_count} snippets")
```

### Query Database

```python
from database import Database, Snippet, Page

db = Database()
with db.get_session() as session:
    # Get all verified snippets
    verified = session.query(Snippet).filter(
        Snippet.status == 'verified'
    ).all()

    for snippet in verified:
        print(f"Snippet {snippet.snippet_id}: {snippet.page.relative_path}")
```

### Custom Pattern Fix

```python
from pattern_registry import PatternFix

# Create custom fix
fix = PatternFix(
    name="Add using directive",
    error_pattern=r"CS0246.*'Archive'",
    old_pattern=r"^",
    new_pattern="using Aspose.Zip;\n",
    description="Add missing using directive"
)

# Apply to code
import re
if re.search(fix.error_pattern, error_message):
    fixed_code = re.sub(fix.old_pattern, fix.new_pattern, original_code, count=1)
```
