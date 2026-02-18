# Example Reviewer System Architecture

## Overview

The Example Reviewer is an automated system for discovering, validating, fixing, and patching C# code snippets in documentation files. It uses a multi-stage pipeline with SQLite persistence, .NET compilation, and AI-powered error fixing.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                        (src/cli.py)                              │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─► discover  ──────────────────────┐
             ├─► validate  ──────────────────────┤
             ├─► patch     ──────────────────────┤
             └─► fix       ──────────────────────┤
                                                  │
┌─────────────────────────────────────────────────▼───────────────┐
│                     Service Layer                                │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │   Discovery    │  │   Validation   │  │    Patching      │  │
│  │    Service     │  │  Orchestrator  │  │    Service       │  │
│  └────────┬───────┘  └───────┬────────┘  └────────┬─────────┘  │
│           │                   │                     │             │
│  ┌────────▼───────┐  ┌───────▼────────┐  ┌────────▼─────────┐  │
│  │     Page       │  │    Example     │  │    Snippet       │  │
│  │    Scanner     │  │     Fixer      │  │    Locator       │  │
│  └────────────────┘  └───────┬────────┘  └──────────────────┘  │
│                              │                                   │
│                      ┌───────▼────────┐                          │
│                      │    Ollama      │                          │
│                      │  Integration   │                          │
│                      └────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
             │                   │                     │
┌────────────▼───────┐  ┌────────▼────────┐  ┌────────▼─────────┐
│     Database       │  │   Workspace     │  │     Pattern      │
│   (SQLite ORM)     │  │    Manager      │  │    Registry      │
└────────────────────┘  └─────────────────┘  └──────────────────┘
             │                   │
             │          ┌────────▼────────┐
             │          │  .NET Compiler  │
             │          │  (dotnet build) │
             │          └─────────────────┘
             │
┌────────────▼───────────────────────────────────────────────────┐
│                      Persistence Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  • snippets.db (SQLite)                                         │
│  • workspaces/ (temporary compilation directories)              │
│  • logs/ (telemetry and execution logs)                         │
│  • artifacts/ (validation outputs)                              │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Interface (`cli.py`)

**Purpose**: Command-line entry point for all operations

**Commands**:
- `discover`: Scan markdown files and extract code snippets
- `validate`: Compile and verify snippets
- `patch`: Apply verified code to original files
- `fix`: AI-powered error correction

**Responsibilities**:
- Argument parsing
- Command routing
- Database initialization
- Error handling and user feedback

### 2. Discovery Service (`discovery_service.py`)

**Purpose**: Find and extract code snippets from markdown files

**Components**:
- **PageScanner**: Parse markdown and locate code fences
- **SnippetLocator**: Create locator metadata (hashes, context, ordinals)

**Process**:
1. Glob markdown files by family pattern
2. Parse each file for code fences
3. Extract snippet content and context
4. Generate locator metadata
5. Store in database

**Locator Metadata**:
```json
{
  "snippet_content_hash": "sha256_of_code",
  "heading_context": ["Parent Heading", "Child Heading"],
  "snippet_ordinal": 1,
  "file_relative_path": "content/blog.aspose.net/zip/..."
}
```

### 3. Validation Orchestrator (`validation_orchestrator.py`)

**Purpose**: Compile and verify code snippets

**Process**:
1. Create isolated workspace per snippet
2. Apply pattern-based fixes
3. Wrap code in library-compatible class
4. Compile with `dotnet build`
5. Parse compiler output
6. Store results in database

**Workspace Structure**:
```
workspaces/
  snippet_123/
    Program.cs         # Wrapped snippet
    Validator.csproj   # .NET project
    bin/              # Build output
    obj/              # Build cache
```

### 4. Example Fixer (`example_fixer.py`)

**Purpose**: Fix compilation errors using patterns and AI

**Fix Strategies**:
1. **Pattern-based**: Apply known fixes from registry
2. **Ollama AI**: Send errors to LLM for intelligent fixes
3. **Iterative**: Retry compilation up to max attempts

**Fix Registry** (`pattern_registry.py`):
- Pattern matching on error messages
- Predefined code transformations
- Family-specific fix rules

### 5. Patching Service (`patching_service.py`)

**Purpose**: Update original markdown with verified code

**Patching Strategies** (cascading):
1. **Hash Match**: SHA256 content matching (most reliable)
2. **Heading Context**: Match by document structure + ordinal
3. **Fuzzy Match**: Similarity-based matching (last resort)

**Verification**:
- Post-patch code fence validation
- Ensure verified code appears in fence
- No code leakage outside fences

### 6. Workspace Manager (`workspace_manager.py`)

**Purpose**: Manage isolated compilation environments

**Features**:
- Temporary directory creation
- .csproj and Program.cs generation
- Library-mode compilation (no Main method)
- Cleanup after validation

**Wrapper Template**:
```csharp
using System;
using System.IO;
// ... other usings

public class SnippetValidator
{
    public static void ValidateSnippet()
    {
        // USER CODE INJECTED HERE
    }
}
```

### 7. Database (`database.py`)

**Purpose**: Persist all system state

**Tables**:
- `pages`: Markdown files being processed
- `snippets`: Extracted code snippets
- `validation_runs`: Validation execution metadata
- `validation_results`: Compilation outcomes per snippet

**ORM**: SQLAlchemy with declarative models

### 8. Ollama Integration (`ollama_integration.py`)

**Purpose**: AI-powered code fixing

**Process**:
1. Format error context (original code, errors, patterns)
2. Send to Ollama API with structured prompt
3. Parse AI response for fixed code
4. Validate fix with compilation

**Model**: Configurable (default: llama3.1)

## Data Flow

### Discovery Flow

```
Markdown Files
    │
    ├─► PageScanner.scan_files()
    │       ├─► Regex: find C# code fences
    │       ├─► Extract snippet content
    │       └─► Build heading context
    │
    ├─► SnippetLocator.create_locator()
    │       ├─► Hash: SHA256(snippet)
    │       ├─► Context: heading hierarchy
    │       └─► Ordinal: position in page
    │
    └─► Database.save()
            ├─► INSERT INTO pages
            └─► INSERT INTO snippets
```

### Validation Flow

```
Database Snippets
    │
    ├─► ValidationOrchestrator.run()
    │       ├─► Create validation_run
    │       └─► For each snippet:
    │               │
    │               ├─► WorkspaceManager.create()
    │               │       ├─► mkdir workspaces/snippet_N
    │               │       ├─► Write Program.cs
    │               │       └─► Write Validator.csproj
    │               │
    │               ├─► PatternRegistry.apply_fixes()
    │               │       └─► Transform code
    │               │
    │               ├─► WorkspaceWrapper.wrap_code()
    │               │       └─► Inject into class method
    │               │
    │               ├─► subprocess: dotnet build
    │               │       ├─► Parse stdout/stderr
    │               │       └─► Extract errors
    │               │
    │               └─► Database.save_result()
    │                       └─► INSERT INTO validation_results
    │
    └─► Status: verified | needs_fix | error
```

### Fixing Flow

```
Failed Validation Results
    │
    ├─► ExampleFixer.fix_snippet()
    │       │
    │       ├─► Pattern Fixes First
    │       │       ├─► PatternRegistry.match()
    │       │       ├─► Apply transformation
    │       │       └─► Revalidate
    │       │
    │       └─► If still fails: Ollama
    │               ├─► Format context
    │               ├─► POST to Ollama API
    │               ├─► Parse AI response
    │               ├─► Apply suggested fix
    │               └─► Revalidate
    │
    └─► Update snippet in database
```

### Patching Flow

```
Verified Snippets
    │
    ├─► PatchingService.patch_family()
    │       │
    │       └─► For each verified snippet:
    │               │
    │               ├─► Read original markdown file
    │               │
    │               ├─► Strategy 1: Hash Match
    │               │       ├─► Find fence with matching SHA256
    │               │       └─► If found: use position
    │               │
    │               ├─► Strategy 2: Heading Context
    │               │       ├─► Parse markdown structure
    │               │       ├─► Match heading hierarchy
    │               │       └─► Use ordinal position
    │               │
    │               ├─► Strategy 3: Fuzzy Match
    │               │       ├─► Compute similarity scores
    │               │       └─► Use best match
    │               │
    │               ├─► Replace fence content
    │               │       ├─► Extract language tag
    │               │       └─► Build: ```lang\ncode\n```
    │               │
    │               ├─► Verify patch
    │               │       └─► Check code in fence
    │               │
    │               └─► Write modified file
    │
    └─► Dry-run mode: skip write
```

## Design Patterns

### 1. Service Pattern
- Each major operation is a dedicated service class
- Services are stateless and injected with dependencies
- Clear separation of concerns

### 2. Strategy Pattern
- Patching uses cascading strategies (hash → context → fuzzy)
- Fixing uses pattern-based then AI-based strategies
- Allows flexible algorithm selection

### 3. Repository Pattern
- Database access abstracted through ORM models
- Services interact with high-level database APIs
- Easy to swap persistence layer

### 4. Template Method Pattern
- WorkspaceWrapper defines template for code wrapping
- Subclasses can customize specific steps
- Consistent structure across snippets

### 5. Command Pattern
- CLI commands map to service operations
- Each command is self-contained
- Easy to add new commands

## Configuration

### Database
- Location: `data/snippets.db` (configurable)
- Auto-creates schema on first run
- SQLite for portability

### Workspace
- Base path: `workspaces/`
- Cleanup: Manual or automatic
- Isolation: One directory per snippet

### Compilation
- Framework: net8.0
- Mode: Library (OutputType=Library)
- Packages: Aspose.Zip (configurable version)

### Ollama
- URL: `http://localhost:11434`
- Model: `llama3.1` (configurable)
- Temperature: 0 (deterministic)

## Error Handling

### Graceful Degradation
- Discovery: Skip malformed files, log errors
- Validation: Capture all errors in database
- Patching: Dry-run mode for safety

### Error Categories
- **Discovery Errors**: Invalid markdown, missing files
- **Compilation Errors**: Syntax, type, namespace errors
- **Patching Errors**: Cannot locate fence, verification failed
- **System Errors**: Database corruption, network issues

### Logging
- Console: User-facing messages with color coding
- Files: Detailed logs in `logs/`
- Telemetry: Metrics and timing in database

## Scalability Considerations

### Performance
- Batch processing: Process snippets in parallel (future)
- Caching: Reuse workspaces when possible
- Incremental: Only re-validate changed snippets

### Limitations
- SQLite: Single-writer limitation (suitable for single-user)
- Workspace: Disk I/O can be slow with many snippets
- Ollama: Network latency for API calls

### Future Improvements
- Parallel validation with process pool
- PostgreSQL support for multi-user
- Workspace pooling for faster validation
- Caching of compilation results

## Security Considerations

### Code Execution
- Isolated workspaces prevent cross-contamination
- No network access in compiled code
- Temporary directories cleaned up

### Input Validation
- Markdown parsing uses safe regex
- File paths validated before access
- SQL injection prevented by ORM

### Secrets Management
- No credentials stored in database
- Ollama API uses local endpoint
- NuGet packages from trusted sources

## Extension Points

### Adding New Families
1. Update discovery patterns in PageScanner
2. Add NuGet packages to workspace template
3. Create family-specific pattern fixes

### Custom Fix Strategies
1. Implement pattern in PatternRegistry
2. Add regex matcher and transformer
3. Configure priority order

### Alternative Compilation
1. Subclass WorkspaceWrapper
2. Override compilation method
3. Parse alternative output format

### Different Persistence
1. Implement database interface
2. Create migration scripts
3. Update dependency injection

## Testing Strategy

### Unit Tests
- Pattern registry matching
- Locator hash generation
- Code similarity calculations

### Integration Tests
- Discovery → Database
- Validation → Workspace → Compilation
- Patching → File modification

### End-to-End Tests
- Full pipeline on sample data
- Verify database state
- Check file modifications

## Monitoring and Observability

### Metrics
- Discovery: Files scanned, snippets found
- Validation: Success rate, compilation time
- Fixing: Pattern vs AI fix ratio
- Patching: Success rate, strategies used

### Logging Levels
- DEBUG: Detailed execution flow
- INFO: User-facing progress
- WARN: Recoverable errors
- ERROR: Fatal errors

### Telemetry
- Stored in database tables
- Query for analytics
- Export to visualization tools
