# Documentation Plan: IH-03 - Architecture Documentation Alignment

**Agent**: Agent D (Docs & Specs)
**Task**: IH-03
**Priority**: P2 (MEDIUM)
**Date**: 2026-01-16 22:00 PKT

## Objective

Align architecture.md with the current implementation by comprehensively documenting all pipeline phases, services, database schema, configuration system, and quality gates.

## Current State Analysis

### Existing Documentation (docs/architecture.md)
The current architecture.md covers:
- Discovery service with gist support
- Validation orchestrator
- Patching service with gist modes
- Database layer with gist tables
- Persistent fix service with context inference
- Basic data flows

### Missing/Outdated Elements
1. **Multi-phase pipeline**: Not documented (A-F phases)
2. **Telemetry system**: Missing comprehensive coverage
3. **Git commit automation**: Phase F not documented
4. **Namespace validation**: Not mentioned
5. **Pattern detection**: Not mentioned
6. **Dependency resolution**: Not mentioned
7. **Database schema**: Incomplete (missing review tables, telemetry runs)
8. **Service layer**: Many services undocumented
9. **Configuration hierarchy**: Not explained
10. **Quality gates**: Not documented
11. **Extensibility points**: Missing

## Documentation Structure Plan

### 1. System Overview
- High-level architecture diagram (Mermaid)
- Component interaction overview
- Technology stack
- Design principles

### 2. Pipeline Architecture
- **Phase A**: Discovery and Extraction
- **Phase B**: Compilation Verification Loop
- **Phase C**: Runtime Verification Loop
- **Phase D**: Markdown Update
- **Phase E**: Final LLM Review
- **Phase F**: Persist, Telemetry, Commit

Each phase documented with:
- Purpose and goals
- Input/output
- Flow diagram
- Key services involved
- Error handling
- Source code references

### 3. Service Layer Documentation

#### Core Services
- **DiscoveryService**: Content scanning and snippet extraction
- **CompilationService**: C# compilation with .NET SDK
- **RuntimeService**: Code execution with test data
- **MarkdownUpdateService**: Content patching and diff generation
- **LLMService**: OpenAI/Ollama integration for code fixing

#### Supporting Services
- **TelemetryService**: HTTP API and local telemetry tracking
- **VectorDBService**: ChromaDB for similarity search
- **ResourceDetectionService**: GPU/CPU detection and allocation
- **BackfillService**: Auto-download missing test data/API refs
- **GistPublisher**: GitHub Gist upload/management

### 4. Database Schema
- ER diagram (ASCII art or Mermaid)
- Core tables:
  - example_records
  - compile_attempts
  - runtime_attempts
  - markdown_edits
  - commit_records
  - run_records
  - telemetry_events
  - telemetry_runs
  - review_results
  - review_issues
  - api_reference_cache
  - gist_publications

### 5. Configuration System
- Global config (config/global.json)
- Family configs (config/families/*.json)
- Environment variable overrides
- CLI parameter overrides
- Configuration precedence hierarchy
- Pydantic models and validation

### 6. Quality Gates
- Namespace validation
- Pattern detection
- Drift detection (cascading degradation prevention)
- Infinite loop detection (3-strike rule)
- Final LLM review with consensus voting
- Review issue tracking

### 7. Extensibility Points
- Adding new families
- Adding new validators
- Adding new patterns
- Custom LLM providers
- Custom telemetry endpoints
- Custom quality gates

### 8. Data Flow Diagrams
- Discovery → Compilation → Runtime → Markdown → Review → Commit
- LLM context enrichment (API ref, similar examples)
- Vector DB integration flow
- Telemetry collection flow

## Implementation Strategy

### Step 1: Preserve Existing Content
- Read current architecture.md
- Mark outdated sections with "DEPRECATED:" prefix
- Preserve gist-specific documentation (still relevant)

### Step 2: Write New Sections
- Add "## System Overview" at the top
- Add "## Multi-Phase Pipeline Architecture"
- Expand "## Service Layer"
- Add "## Database Schema"
- Add "## Configuration System"
- Add "## Quality Gates"
- Add "## Extensibility Points"

### Step 3: Update Existing Sections
- Update "## Core Components" with new services
- Update "## Data Flow" with multi-phase flow
- Merge context inference documentation
- Add references to source code with line numbers

### Step 4: Add Update Notice
- Add "## Update — 2026-01-16 22:00 PKT" section at end
- List all major changes
- Add migration notes if needed

## Verification Plan

### Link Verification
- Verify all source file references exist
- Check line numbers for key functions
- Test relative links to other docs

### Code Reference Verification
```bash
# Verify mentioned classes exist
grep -r "class PipelineOrchestrator" src/
grep -r "class DiscoveryService" src/
grep -r "class CompilationService" src/
grep -r "class RuntimeService" src/
grep -r "class MarkdownUpdateService" src/
grep -r "class LLMService" src/
grep -r "class TelemetryService" src/
grep -r "class VectorDBService" src/
grep -r "class ResourceDetectionService" src/
grep -r "class BackfillService" src/

# Verify mentioned tables exist
grep "CREATE TABLE.*example_records" src/core/database.py
grep "CREATE TABLE.*compile_attempts" src/core/database.py
grep "CREATE TABLE.*runtime_attempts" src/core/database.py
grep "CREATE TABLE.*review_results" src/core/database.py
grep "CREATE TABLE.*telemetry_runs" src/core/database.py
```

### Diagram Verification
- Ensure Mermaid diagrams render correctly
- Test ASCII art alignment
- Validate flowchart syntax

### Accuracy Verification
- Cross-reference with orchestrator.py implementation
- Verify phase names match code
- Confirm database schema matches SCHEMA constant
- Validate configuration field names

## Source Files to Reference

### Primary Sources
- `src/pipeline/orchestrator.py` (lines 1-1349)
- `src/core/database.py` (lines 1-1511)
- `src/core/config.py` (lines 1-445)
- `src/core/models.py` (status enums, data models)
- `src/core/telemetry.py` (telemetry tracking)

### Service Sources
- `src/services/discovery_service.py`
- `src/services/compilation_service.py`
- `src/services/runtime_service.py`
- `src/services/markdown_service.py`
- `src/services/llm_service.py`
- `src/services/telemetry_service.py`
- `src/services/vector_db_service.py`
- `src/services/resource_detection_service.py`
- `src/services/backfill_service.py`
- `src/services/gist_publisher.py`

### Configuration Sources
- `config/global.json` (global defaults)
- `config/families/zip.json` (example family config)
- `README.md` (high-level overview)

## Deliverables

1. **docs/architecture.md** - Comprehensive architecture documentation
2. **plan.md** - This document
3. **changes.md** - List of all sections updated
4. **evidence.md** - Verification results for all references
5. **self_review.md** - 12-dimension quality assessment
6. **commands.sh** - Verification commands used

## Success Criteria

- [ ] All pipeline phases documented (A-F)
- [ ] All services documented with responsibilities
- [ ] Database schema complete with ER diagram
- [ ] Configuration hierarchy explained
- [ ] Quality gates section comprehensive
- [ ] Code examples for extension points
- [ ] All links verified and working
- [ ] No contradictions with actual code
- [ ] All mentioned files/classes/functions exist
- [ ] Diagrams render correctly
- [ ] Self-review scores ≥4/5 on all dimensions
