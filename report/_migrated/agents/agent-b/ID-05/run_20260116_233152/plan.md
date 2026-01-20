# Implementation Plan: ID-05 - Selective Vector DB Storage

**Agent**: Agent B (Implementation Specialist)
**Task ID**: ID-05
**Priority**: P2 (MEDIUM)
**Estimated Time**: 8 hours
**Date**: 2026-01-16
**Run ID**: run_20260116_233152

## Executive Summary

Implement selective vector DB storage that filters out high-drift examples to prevent "drift contagion" where drifted code examples pollute the vector DB and lead to similar-but-wrong code being suggested.

## Problem Analysis

### Current State
- VectorDBService stores ALL verified examples, regardless of drift score
- No drift filtering during storage
- Single collection "verified_examples" for all examples
- Search returns all examples without drift consideration
- High-drift examples can cause similar drift in other fixes (contagion)

### Gaps Identified
- ID-GAP-05: Vector DB stores drifted examples causing contagion
- No drift_score parameter in add_example()
- No exclude_high_drift parameter in search_similar()
- No cleanup method for removing high-drift examples
- No separate collections for original vs fixed examples

### Dependencies Status
✅ ID-02 (Drift Threshold Gate) - COMPLETE
- DriftDetector service available at src/services/drift_detector.py
- drift_score computed in orchestrator (lines 597-632, 972-1006)
- Database has drift_score columns in snippets table

✅ VectorDBService - EXISTS
- Location: src/services/vector_db_service.py
- Has add_example(), search_similar(), get_example(), delete_example()
- Uses ChromaDB with sentence-transformers embeddings
- Single collection "verified_examples"

## Solution Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                     │
│  (computes drift_score via DriftDetector)                   │
└────────────────────────┬────────────────────────────────────┘
                         │ drift_score
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    VectorDBService                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ add_example(example_id, code, metadata, drift_score)   │ │
│  │   ├─ Check drift_score against threshold (0.3)        │ │
│  │   ├─ If drift_score >= threshold: reject, return False│ │
│  │   ├─ Add drift_score to metadata                      │ │
│  │   ├─ Route to collection (original vs fixed)          │ │
│  │   └─ Store in ChromaDB                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ search_similar(query, family, k, exclude_high_drift)   │ │
│  │   ├─ Search both collections                          │ │
│  │   ├─ If exclude_high_drift: filter drift_score >= 0.3 │ │
│  │   ├─ Combine and sort by similarity                   │ │
│  │   └─ Return top k results                             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ clean_high_drift(family, max_drift)                    │ │
│  │   ├─ Query all examples for family                    │ │
│  │   ├─ Filter examples with drift_score >= max_drift    │ │
│  │   ├─ Delete high-drift examples                       │ │
│  │   └─ Return count of removed examples                 │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                        ChromaDB                              │
│  ┌──────────────────┐    ┌─────────────────┐               │
│  │original_examples │    │ fixed_examples  │               │
│  │  (no LLM fixes) │    │ (LLM-fixed code)│               │
│  └──────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Drift Threshold**: Default 0.3 (from global_config.drift.threshold)
2. **Separate Collections**:
   - "original_examples": Code that compiled first try
   - "fixed_examples": Code fixed by LLM
3. **Drift Score in Metadata**: Always store drift_score for observability
4. **Backwards Compatible**: drift_score parameter is optional (defaults to None)
5. **Graceful Degradation**: If vector DB unavailable, return False/0 without raising exceptions

### Migration Strategy

**Forward-Compatible Migration**:
- Existing "verified_examples" collection remains (will be deprecated)
- New code uses "original_examples" and "fixed_examples"
- Old data continues to work (no drift_score in metadata = passes filter)
- No database migration required

## Implementation Steps

### Step 1: Update VectorDBService (src/services/vector_db_service.py)

**READ FIRST**: Lines 1-337 to understand existing structure

**Changes**:

1. **Update add_example() method** (lines 121-159)
   - Add drift_score parameter (optional, default None)
   - Add drift threshold check (use metadata.get('drift_threshold', 0.3))
   - If drift_score >= threshold: log and return False
   - Add drift_score to metadata if not None
   - Route to collection based on source (original vs fixed)
   - Call _get_collection() helper

2. **Update search_similar() method** (lines 161-223)
   - Add exclude_high_drift parameter (default True)
   - Search both "original_examples" and "fixed_examples" collections
   - Filter results by drift_score if exclude_high_drift=True
   - Combine results and sort by similarity
   - Return top k results

3. **Add _get_collection() helper method** (new)
   - Get or create collection by name
   - Handle ChromaDB exceptions gracefully

4. **Add clean_high_drift() method** (new)
   - Accept family and max_drift parameters
   - Query all examples for family in both collections
   - Filter by drift_score >= max_drift
   - Delete high-drift examples in batch
   - Return count of removed examples

**Estimated Changes**: ~150 lines (additions + modifications)

### Step 2: Update Orchestrator (src/pipeline/orchestrator.py)

**READ FIRST**: Lines 456-746 (compilation phase), 748-1158 (runtime phase)

**Integration Points**:

1. **Compilation phase** (lines 503-518, 711-728)
   - Pass drift_score to vector_db_service.add_example()
   - For first-try compilable: drift_score=None (no LLM fix)
   - For LLM-fixed compilable: drift_score from lines 701-710

2. **Runtime phase** (lines 860-874, 1096-1113)
   - Pass drift_score to vector_db_service.add_example()
   - For first-try verified: drift_score=None
   - For LLM-fixed verified: drift_score from lines 1085-1095

**Estimated Changes**: 4 call sites, ~10 lines

### Step 3: Add CLI Command (src/cli/main.py)

**READ FIRST**: Lines 1-268 to understand CLI structure

**Changes**:

1. **Add clean_vector_db() function** (new, after line 258)
   - Initialize database and vector_db_service
   - Call clean_high_drift()
   - Print results

2. **Add CLI parser** (after line 157)
   - Add subparser for 'clean-vector-db'
   - Arguments: --family (required), --max-drift (default 0.3)
   - Set handler to clean_vector_db

**Estimated Changes**: ~30 lines

### Step 4: Create Test Suite (tests/test_selective_vector_db.py)

**NEW FILE**: ~300 lines

**Test Cases**:

1. test_high_drift_examples_not_stored
   - Add example with drift_score=0.8
   - Verify not stored (add_example returns False)

2. test_low_drift_examples_stored
   - Add example with drift_score=0.1
   - Verify stored successfully (add_example returns True)

3. test_drift_metadata_in_vector_db
   - Add example with drift_score
   - Retrieve and verify drift_score in metadata

4. test_search_excludes_high_drift
   - Add low and high drift examples
   - Search with exclude_high_drift=True
   - Verify only low-drift returned

5. test_search_can_include_high_drift
   - Search with exclude_high_drift=False
   - Verify high-drift examples included

6. test_cleanup_removes_high_drift
   - Add examples with various drift scores
   - Run clean_high_drift()
   - Verify high-drift removed, low-drift kept

7. test_separate_collections_for_fixed
   - Add example with source='llm_fixed'
   - Verify stored in 'fixed_examples' collection
   - Add example without source
   - Verify stored in 'original_examples' collection

8. test_vector_db_unavailable_graceful
   - Mock vector DB as unavailable
   - Verify methods return False/0 gracefully

9. test_backwards_compatible_no_drift_score
   - Add example without drift_score (None)
   - Verify stored successfully (no filtering)

10. test_custom_drift_threshold
    - Add example with drift_score=0.25
    - Use metadata drift_threshold=0.2
    - Verify rejected

**Test Fixtures**:
- vector_db: VectorDBService with in-memory ChromaDB
- mock_orchestrator: For integration tests

**Estimated Lines**: ~300 lines

## Testing Strategy

### Unit Tests
- Test VectorDBService methods in isolation
- Mock ChromaDB when needed
- Test graceful degradation (unavailable state)
- Test backwards compatibility

### Integration Tests
- Test orchestrator → vector_db_service flow
- Test CLI command end-to-end
- Test with real ChromaDB (if available)

### Acceptance Criteria Validation
- [ ] VectorDBService.add_example() accepts drift_score parameter
- [ ] High-drift examples (drift >= 0.3) are not stored in vector DB
- [ ] Low-drift examples (drift < 0.3) are stored successfully
- [ ] drift_score included in vector DB metadata
- [ ] search_similar() has exclude_high_drift parameter (default True)
- [ ] Search excludes high-drift examples by default
- [ ] clean_high_drift() method removes high-drift examples
- [ ] Separate "original_examples" and "fixed_examples" collections
- [ ] CLI command 'clean-vector-db' works
- [ ] Orchestrator passes drift_score to vector DB
- [ ] Unit tests pass (8+ tests)
- [ ] Graceful handling when vector DB unavailable
- [ ] Zero breaking changes to existing vector DB functionality

## Risk Assessment

### Low Risk
- VectorDBService changes are additive (new parameters optional)
- Orchestrator changes are minimal (add parameter to existing calls)
- CLI command is new (no existing code affected)

### Medium Risk
- ChromaDB collection changes (new collections created)
- Search logic becomes more complex (multiple collections)

### Mitigation Strategies
1. **Backwards Compatibility**:
   - drift_score=None defaults to no filtering
   - Existing code continues to work
2. **Graceful Degradation**:
   - All methods return False/0 if unavailable
   - No exceptions raised
3. **Testing**:
   - Comprehensive unit tests
   - Integration tests with real ChromaDB
   - Test unavailable state

## Performance Considerations

### Expected Overhead
- Drift filtering: < 1ms per example (metadata check)
- Collection routing: < 1ms (simple if-else)
- Search filtering: ~10-50ms (depends on result count)
- Cleanup: O(n) where n = examples in family

### Optimization Opportunities
- Batch deletion in clean_high_drift() (already planned)
- Index on drift_score in ChromaDB metadata (if supported)

## Backwards Compatibility

### Existing Code
- All existing vector_db_service calls continue to work
- drift_score parameter is optional (defaults to None)
- If drift_score is None, no filtering applied (store all)

### Existing Data
- Old examples in "verified_examples" collection remain accessible
- No drift_score in metadata = passes filter (treated as low-drift)

### Migration Path
- Phase 1: Deploy new code (this task)
- Phase 2: Gradually populate drift_scores in metadata
- Phase 3: Eventually deprecate "verified_examples" collection

## Observability

### Logging
- Log when example rejected due to drift: `INFO` level
- Log drift_score for all stored examples: `DEBUG` level
- Log cleanup operations: `INFO` level with count

### Metrics (for future telemetry)
- Count of examples rejected due to drift
- Distribution of drift_scores in vector DB
- Cleanup operation counts

## Dependencies

### Python Packages (already installed)
- chromadb >= 0.4.20 (optional)
- sentence-transformers >= 2.2.0 (optional)
- numpy (for drift computation)

### Internal Dependencies
- DriftDetector (src/services/drift_detector.py) ✅
- Database with drift_score columns ✅
- Global config with drift threshold ✅

## Timeline

1. **Plan Phase** (30 min): Create this plan ✅
2. **Implementation Phase** (4 hours):
   - Update VectorDBService (2 hours)
   - Update orchestrator (30 min)
   - Add CLI command (30 min)
   - Create test suite (1 hour)
3. **Test Phase** (2 hours): Run tests, fix issues
4. **Evidence Phase** (1 hour): Document test outputs
5. **Self-Review Phase** (30 min): 12-dimension quality assessment

**Total**: ~8 hours (as estimated)

## Success Criteria

### Functional
- All 13 acceptance criteria met
- Unit tests pass (8+ tests, 100% coverage)
- Integration tests pass
- CLI command works end-to-end

### Quality
- All 12 dimensions score ≥4/5
- Zero breaking changes
- Code follows existing patterns
- Comprehensive error handling

## Next Steps

1. Review plan with stakeholders (if needed)
2. Begin implementation (Step 1: VectorDBService)
3. Iterate on test failures
4. Document evidence
5. Perform self-review

## References

- Task specification: ID-05 in plans/healing/intent-drift-prevention.md lines 1305-1551
- DriftDetector implementation: src/services/drift_detector.py
- VectorDBService current implementation: src/services/vector_db_service.py
- Orchestrator drift detection: src/pipeline/orchestrator.py lines 597-632, 972-1006
- Existing test patterns: tests/test_vector_db_service.py
