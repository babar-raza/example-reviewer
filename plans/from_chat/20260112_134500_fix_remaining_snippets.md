# Fix Remaining Validation Snippet Failures

**Date**: 2026-01-12 13:45
**Context**: Post API Reference Enhancement - Fix snippets 136, 139, 140
**Status**: PLANNING
**Priority**: HIGH

---

## Context

After implementing API reference enhancements with negative guidance and usage patterns:
- ✅ **Run 29**: Snippet 138 successfully fixed in 2 iterations (25% success rate)
- ❌ **Remaining failures**: Snippets 136, 139, 140 still failing

**Quote from chat**:
> "Not fixed yet:
> - Snippet 136: Context inference creates malformed code (needs separate fix)
> - Snippets 139, 140: Different error patterns (need additional patterns)"

**Evidence files**:
- `VALIDATION_FAILURE_ANALYSIS.md` - Root cause analysis
- `API_REFERENCE_ENHANCEMENT_RESULTS.md` - Enhancement results

---

## Goals

1. **Fix snippet 136**: Correct context inference wrapper to generate valid C# code structure
2. **Fix snippets 139 & 140**: Identify error patterns and add appropriate API usage patterns
3. **Achieve 100% success rate**: All 4 test snippets (136, 138, 139, 140) verify successfully
4. **Maintain quality**: All fixes must pass existing tests and not break snippet 138

---

## Assumptions (UNVERIFIED → Must verify)

### Snippet 136
- [ ] **UNVERIFIED**: Context inference is enabled and generating wrapper code
- [ ] **UNVERIFIED**: Malformed code has `using` statements inside class body
- [ ] **UNVERIFIED**: Issue is in `src/validation_orchestrator.py` or context inference logic
- [ ] **UNVERIFIED**: Original snippet code is valid when properly wrapped

### Snippets 139 & 140
- [ ] **UNVERIFIED**: These snippets have different error patterns than 136 and 138
- [ ] **UNVERIFIED**: Errors are API-related (not structural like 136)
- [ ] **UNVERIFIED**: Can be fixed with additional patterns in family config
- [ ] **UNVERIFIED**: Not fundamentally unfixable (contain usable APIs)

---

## Steps (Concrete, repo-specific after verification)

### Phase 1: Investigation & Evidence Gathering

**Agent**: A (Discovery & Architecture)

1. **Verify snippet 136 assumptions**
   ```bash
   # Query database for snippet 136 details
   python -c "from database import Database; ..." # Get original code, errors, generated code
   ```
   - Read snippet 136 original code from database
   - Read latest compilation errors from Run 29
   - Read generated code (if context inference was used)
   - Confirm malformed structure matches VALIDATION_FAILURE_ANALYSIS.md

2. **Locate context inference logic**
   ```bash
   grep -r "context.*inference" src/
   grep -r "def.*wrap\|def.*infer" src/
   ```
   - Find where wrapper code is generated
   - Identify current wrapper template/logic
   - Document current behavior vs expected behavior

3. **Verify snippets 139 & 140 assumptions**
   ```bash
   # Query database for snippets 139, 140 details
   python -c "..." # Get errors, attempts, code evolution
   ```
   - Read original code for both snippets
   - Read compilation errors from Run 29
   - Read LLM-generated code from all attempts
   - Identify common error patterns
   - Check if errors are structural or API-related

**Deliverables**:
- `reports/agents/discovery/snippet_136_investigation/evidence.md` with:
  - Original code, errors, generated code
  - Context inference code location and logic
  - Gap analysis: current vs correct wrapper structure
- `reports/agents/discovery/snippets_139_140_investigation/evidence.md` with:
  - Original code, errors, code evolution
  - Error pattern classification
  - Required patterns identification

### Phase 2: Implementation - Fix Snippet 136

**Agent**: B (Implementation)

**Prerequisites**: Phase 1 complete, context inference location confirmed

4. **Design correct wrapper structure**
   - Document expected wrapper format (using at top, namespace/class below)
   - Identify minimal change to fix issue
   - Plan rollback strategy

5. **Implement context inference fix**
   - Modify wrapper generation logic in identified file
   - Ensure `using` statements placed at top level
   - Preserve original snippet code structure
   - Add comments explaining wrapper structure

6. **Unit test context inference**
   ```bash
   # Create test for context inference wrapper
   python -m pytest tests/test_context_inference.py -v
   ```
   - Test with snippet that needs wrapper
   - Verify correct structure generated
   - Test edge cases (already has using, already has namespace, etc.)

**Deliverables**:
- Modified file with fix (likely `src/validation_orchestrator.py` or similar)
- `reports/agents/implementation/snippet_136_fix/changes.md` documenting:
  - Files changed with diffs
  - Logic explanation
  - Rollback plan
- `reports/agents/implementation/snippet_136_fix/evidence.md` with:
  - Unit test results
  - Before/after wrapper code examples

### Phase 3: Implementation - Fix Snippets 139 & 140

**Agent**: B (Implementation)

**Prerequisites**: Phase 1 complete, error patterns identified

7. **Add API patterns to family config**
   - Add patterns for identified error scenarios
   - Follow format from existing patterns in `config/families/zip.json`
   - Ensure patterns show correct API usage clearly

8. **Test pattern effectiveness**
   ```bash
   # Query what patterns will be included in prompts
   python -c "from ollama_integration import OllamaClient; ..." # Test prompt generation
   ```
   - Verify patterns are loaded from config
   - Verify patterns are included in LLM prompts
   - Verify pattern format is clear and actionable

**Deliverables**:
- Modified `config/families/zip.json` with new patterns
- `reports/agents/implementation/snippets_139_140_fix/changes.md` documenting:
  - Patterns added with explanations
  - Why these patterns address the errors
- `reports/agents/implementation/snippets_139_140_fix/evidence.md` with:
  - Pattern extraction test results
  - Prompt generation examples

### Phase 4: Integration Testing

**Agent**: C (Tests & Verification)

**Prerequisites**: Phases 2 & 3 complete

9. **Reset test snippets and run validation**
   ```bash
   # Reset snippets 136, 139, 140 to unverified
   python -c "from database import Database; db = Database('data/examples.db'); db.connect(); [db.update_snippet(id, status='unverified') for id in [136,139,140]]; db._conn.commit()"

   # Run validation
   python src/cli.py validate --family zip --content-root "D:\path\to\content" --max-snippets 5
   ```
   - Capture full output
   - Monitor metrics (api_context_extracted, iterations, successes)
   - Check artifacts directory for detailed logs

10. **Verify all test snippets**
    ```bash
    # Query results from database
    python -c "..." # Check snippet statuses, fix sessions, final code
    ```
    - Snippet 136: status should be 'verified'
    - Snippet 138: status should remain 'verified' (regression check)
    - Snippet 139: status should be 'verified'
    - Snippet 140: status should be 'verified'
    - All should have reasonable iteration counts (<=5)

11. **Test edge cases**
    - Run validation on different ZIP blog posts
    - Ensure no regressions in previously verified snippets
    - Check that context inference doesn't break non-inferred snippets

**Deliverables**:
- `reports/agents/tests/integration_validation/evidence.md` with:
  - Full validation run output
  - Database query results showing all 4 snippets verified
  - Metrics comparison (Run 29 vs new run)
  - Final working code for all snippets
  - Screenshots/logs of successful compilation

### Phase 5: Documentation

**Agent**: D (Docs & Specs)

**Prerequisites**: Phase 4 complete, all tests passing

12. **Update analysis documents**
    - Append results to `VALIDATION_FAILURE_ANALYSIS.md`
    - Append results to `API_REFERENCE_ENHANCEMENT_RESULTS.md`
    - Document context inference fix

13. **Create fix summary document**
    - New file: `SNIPPET_FIX_SUMMARY.md`
    - Document: problem, investigation, solution, results for each snippet
    - Include before/after code examples
    - Include final success metrics

**Deliverables**:
- Updated analysis documents
- `SNIPPET_FIX_SUMMARY.md` with complete fix documentation
- `reports/agents/docs/documentation/evidence.md` with:
  - Links to all updated documents
  - Confirmation all claims backed by evidence

---

## Acceptance Criteria (Tests, outputs, metrics, files)

### Must Pass (Gate for completion)

- [ ] **Snippet 136**: Database status = 'verified', final code compiles successfully
- [ ] **Snippet 138**: Database status remains 'verified' (no regression)
- [ ] **Snippet 139**: Database status = 'verified', final code compiles successfully
- [ ] **Snippet 140**: Database status = 'verified', final code compiles successfully
- [ ] **Success rate**: 100% (4/4 snippets) in final validation run
- [ ] **Iteration count**: All snippets fixed in <=5 iterations
- [ ] **No regressions**: Previously verified snippets remain verified
- [ ] **Context inference**: Generates syntactically valid C# code
- [ ] **Unit tests**: Context inference tests pass
- [ ] **Documentation**: All changes documented with evidence

### Evidence Requirements

- [ ] Database query results showing all snippet statuses
- [ ] Compilation output showing zero errors for all snippets
- [ ] Final working code for all snippets
- [ ] Context inference unit test results
- [ ] Validation run metrics (JSON from artifacts)
- [ ] Before/after comparison for context inference wrapper

---

## Risks + Rollback

### Risk 1: Context inference fix breaks existing snippets
**Mitigation**: Comprehensive testing including previously verified snippets
**Rollback**: Git revert context inference changes, use previous version

### Risk 2: Snippets 139/140 fundamentally unfixable
**Mitigation**: Investigate thoroughly before attempting patterns
**Rollback**: Mark snippets as "needs-manual-fix", document why unfixable

### Risk 3: New patterns confuse LLM for other snippets
**Mitigation**: Test patterns on snippet 138 to ensure no regression
**Rollback**: Remove problematic patterns from family config

### Risk 4: Context inference fix doesn't address root cause
**Mitigation**: Verify fix with unit tests before integration testing
**Rollback**: Iterate on fix design with additional investigation

---

## Evidence Commands (Exact commands to run)

### Investigation
```bash
# Get snippet 136 details
cd /c/Users/prora/OneDrive/Documents/GitHub/example-reviewer
./venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from database import Database
db = Database(Path('data/examples.db'))
db.connect()
# Query snippet 136 original code, errors, generated code
cursor = db._conn.execute('SELECT code_content FROM snippet_versions WHERE snippet_id = 136 AND version_type = \"original\"')
print('Original Code:', cursor.fetchone()[0])
cursor = db._conn.execute('SELECT compiler_output FROM build_attempts WHERE run_id = 29 AND snippet_id = 136 ORDER BY attempted_at DESC LIMIT 1')
print('Latest Errors:', cursor.fetchone()[0])
cursor = db._conn.execute('SELECT sv.code_content FROM build_attempts ba JOIN snippet_versions sv ON ba.version_id = sv.version_id WHERE ba.run_id = 29 AND ba.snippet_id = 136 ORDER BY ba.attempted_at DESC LIMIT 1')
print('Generated Code:', cursor.fetchone()[0])
"

# Get snippets 139, 140 details
./venv/Scripts/python.exe -c "..." # Similar query for 139, 140

# Find context inference logic
grep -rn "context.*inference" src/ --include="*.py"
grep -rn "def.*wrap" src/ --include="*.py"
```

### Testing
```bash
# Reset test snippets
./venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from database import Database
db = Database(Path('data/examples.db'))
db.connect()
for snippet_id in [136, 139, 140]:
    db.update_snippet(snippet_id, status='unverified')
db._conn.commit()
print('Snippets reset to unverified')
"

# Run validation
./venv/Scripts/python.exe src/cli.py validate --family zip --content-root "D:\\onedrive\\Documents\\GitHub\\aspose.net\\content" --max-snippets 5

# Check results
cat artifacts/runs/run_YYYYMMDD_HHMMSS_NN/metrics.json
./venv/Scripts/python.exe -c "
# Query final statuses and code
"
```

### Verification
```bash
# Check all snippet statuses
./venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, 'src')
from pathlib import Path
from database import Database
db = Database(Path('data/examples.db'))
db.connect()
cursor = db._conn.execute('SELECT snippet_id, status FROM snippets WHERE snippet_id IN (136, 138, 139, 140)')
for row in cursor.fetchall():
    print(f'Snippet {row[0]}: {row[1]}')
"

# Run unit tests for context inference (if created)
./venv/Scripts/python.exe -m pytest tests/test_context_inference.py -v
```

---

## Open Questions (Must be empty by end)

1. **Where exactly is context inference implemented?**
   - [ ] **Resolution**: Grep repo, read validation_orchestrator.py and persistent_fix_service.py
   - [ ] **Status**: OPEN

2. **What specific error patterns do snippets 139/140 have?**
   - [ ] **Resolution**: Query database for their errors, analyze patterns
   - [ ] **Status**: OPEN

3. **Is context inference always enabled or conditional?**
   - [ ] **Resolution**: Read family config, check enable_context_inference flag
   - [ ] **Status**: OPEN

4. **Are snippets 139/140 similar enough to share patterns?**
   - [ ] **Resolution**: Compare their errors and original code
   - [ ] **Status**: OPEN

5. **Do we need to test on more than these 4 snippets?**
   - [ ] **Resolution**: Check total unverified snippets in database, assess risk
   - [ ] **Status**: OPEN

---

## Task Assignment

| Phase | Agent | Priority | Dependencies | Est. Complexity |
|-------|-------|----------|--------------|----------------|
| Phase 1 (Investigation) | A (Discovery) | HIGH | None | MEDIUM |
| Phase 2 (Fix 136) | B (Implementation) | HIGH | Phase 1 | MEDIUM |
| Phase 3 (Fix 139/140) | B (Implementation) | HIGH | Phase 1 | LOW |
| Phase 4 (Integration Test) | C (Tests) | HIGH | Phase 2, 3 | MEDIUM |
| Phase 5 (Documentation) | D (Docs) | MEDIUM | Phase 4 | LOW |

---

**Plan Status**: READY FOR EXECUTION
**Next Step**: Proceed to Step 2 (Discover Work) - Build TASK_BACKLOG.md
