# Implementation Plan: ID-02 Drift Threshold Gate

**Agent**: Agent B (Implementation Specialist)
**Task**: ID-02 - Drift Threshold Gate
**Priority**: P1 (MEDIUM - Prevents runaway drift)
**Estimated Time**: 10 hours
**Status**: READY TO START (ID-04 dependency complete)
**Date**: 2026-01-16

## Mission Statement

Implement drift score computation and threshold gating to prevent LLM from drifting too far from original code during fix iterations. The system must detect when fixes introduce excessive semantic changes and abort the fix loop before code intent is lost.

## Current State Analysis

After reading the codebase, I've identified:

1. **VectorDBService** exists at `src/services/vector_db_service.py`
   - Has `_embedding_model` property (SentenceTransformer instance)
   - Model: "all-MiniLM-L6-v2" (configurable)
   - Already instantiated in `vector_db_service` property of orchestrator
   - Perfect for reuse in drift detection

2. **Orchestrator Fix Loop** at `src/pipeline/orchestrator.py`
   - Compilation phase: Lines 555-672 (LLM fix loop)
   - Runtime phase: Lines 858-1021 (LLM fix loop)
   - Both loops iterate up to `max_retries` times
   - Both update `current_code` with each fix
   - NO drift tracking currently exists

3. **Database Schema** at `src/core/database.py`
   - `example_records` table exists
   - NO drift columns (drift_score, drift_similarity)
   - Schema modification needed

4. **Config System** at `src/core/config.py`
   - Uses Pydantic BaseModel validation
   - GlobalConfig at line 309
   - No DriftConfig exists

5. **Global Config** at `config/global.json`
   - No drift section exists
   - Vector DB enabled: true
   - LLM max_retries: 5

## Problem Analysis

**Risk**: Without drift tracking, LLM can make cumulative changes across iterations that:
- Change the API being demonstrated
- Alter the code intent completely
- Replace examples with unrelated functionality
- By iteration 5, code may be unrecognizable

**Solution**: Compare each LLM-fixed code against **ORIGINAL** code (not previous iteration) to track cumulative drift.

## Implementation Strategy

### Phase 1: Create DriftDetector Service (NEW)

**File**: `src/services/drift_detector.py`

**Design**:
```python
class DriftDetector:
    def __init__(self, model: SentenceTransformer):
        """Reuse embedding model from VectorDBService."""
        self.model = model

    def compute_drift(self, original_code: str, fixed_code: str) -> Tuple[float, float]:
        """
        Returns: (drift_score, similarity)
        - drift_score: 0.0 (identical) to 1.0 (completely different)
        - similarity: 1.0 (identical) to 0.0 (completely different)
        """
        # Embed both codes
        original_embedding = self.model.encode(original_code)
        fixed_embedding = self.model.encode(fixed_code)

        # Cosine similarity
        similarity = np.dot(...) / (norm * norm)
        drift_score = 1.0 - similarity

        return drift_score, similarity
```

**Key Requirements**:
- Accept pre-instantiated SentenceTransformer (NO new instantiation)
- Use numpy for cosine similarity computation
- Return both drift_score and similarity for flexibility

### Phase 2: Update Config System

#### File 1: `src/core/config.py`

Add DriftConfig model:
```python
class DriftConfig(BaseModel):
    enabled: bool = Field(default=True)
    threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    fail_on_exceed: bool = Field(default=True)
    log_all_drift_scores: bool = Field(default=True)
```

Add to GlobalConfig:
```python
class GlobalConfig(BaseModel):
    # ... existing fields ...
    drift: DriftConfig = Field(default_factory=DriftConfig)
```

#### File 2: `config/global.json`

Add drift section after final_review:
```json
"drift": {
  "enabled": true,
  "threshold": 0.3,
  "fail_on_exceed": true,
  "log_all_drift_scores": true
}
```

### Phase 3: Database Schema Update

**File**: `src/core/database.py`

Add drift columns to `example_records` table schema (line 38):
```sql
drift_score REAL,
drift_similarity REAL,
```

Add index for drift queries:
```sql
CREATE INDEX IF NOT EXISTS idx_examples_drift ON example_records(drift_score);
```

**Migration Strategy**:
- Schema uses `CREATE TABLE IF NOT EXISTS`
- New columns will be NULL for existing records
- No data migration needed (safe to add)

### Phase 4: Integrate into Orchestrator

**File**: `src/pipeline/orchestrator.py`

#### Integration Point 1: Compilation Phase (Line ~555-672)

**Current Flow**:
```python
for attempt in range(max_retries):
    # Get LLM fix
    llm_response = self.llm_service.fix_code(...)
    fixed_code = llm_response.content

    # Update and compile
    example.compilable_code = fixed_code
    success, result = self.compilation_service.compile_example(...)

    # Record attempt
    self.compilation_service.record_attempt(...)

    if success:
        # Mark as compilable
        break

    current_code = fixed_code  # CASCADE NEXT ITERATION
```

**New Flow with Drift Detection**:
```python
# Initialize drift detector (once per orchestrator, lazy)
if not hasattr(self, '_drift_detector'):
    from src.services.drift_detector import DriftDetector
    self._drift_detector = DriftDetector(self.vector_db_service._embedding_model)

for attempt in range(max_retries):
    # Get LLM fix
    llm_response = self.llm_service.fix_code(...)
    fixed_code = llm_response.content

    # DRIFT CHECK: Compare against ORIGINAL code
    drift_score, similarity = self._drift_detector.compute_drift(
        original_code=example.original_code,  # KEY: Original, not current_code
        fixed_code=fixed_code
    )

    # Log drift (always)
    if global_config.drift.log_all_drift_scores:
        logger.debug(f"Drift for {example.example_id} attempt {attempt+1}: {drift_score:.3f}")

    # Check threshold
    if global_config.drift.enabled and drift_score > global_config.drift.threshold:
        logger.warning(
            f"Drift threshold exceeded for {example.example_id}: "
            f"{drift_score:.3f} > {global_config.drift.threshold}"
        )

        if global_config.drift.fail_on_exceed:
            # Abort fix loop
            self.db.update_example_status(
                example.example_id,
                ExampleStatus.COMPILE_FAILED,
                failure_reason=f"Drift threshold exceeded ({drift_score:.3f} > {global_config.drift.threshold})"
            )
            stats['failed'] += 1
            break  # Exit retry loop

    # Continue with compilation...
    example.compilable_code = fixed_code
    success, result = self.compilation_service.compile_example(...)

    # Record attempt (with drift score)
    self.compilation_service.record_attempt(...)

    if success:
        # Store final drift score
        self.db.update_example(example_id, drift_score=drift_score, drift_similarity=similarity)
        stats['compiled_with_fix'] += 1
        break

    current_code = fixed_code
```

#### Integration Point 2: Runtime Phase (Line ~858-1021)

**Same pattern**:
- Initialize drift detector (already done)
- Check drift after each LLM fix
- Abort if threshold exceeded
- Store drift score on success

### Phase 5: Database Update Methods

**File**: `src/core/database.py`

Add drift update method:
```python
def update_snippet(
    self,
    example_id: str,
    drift_score: Optional[float] = None,
    drift_similarity: Optional[float] = None,
) -> bool:
    """Update drift tracking fields for an example."""
    with self.get_connection() as conn:
        updates = []
        params = []

        if drift_score is not None:
            updates.append("drift_score = ?")
            params.append(drift_score)

        if drift_similarity is not None:
            updates.append("drift_similarity = ?")
            params.append(drift_similarity)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(example_id)

        conn.execute(
            f"UPDATE example_records SET {', '.join(updates)} WHERE example_id = ?",
            params
        )
        return conn.total_changes > 0
```

### Phase 6: Comprehensive Test Suite

**File**: `tests/test_drift_detector.py`

**Test Cases**:
1. `test_drift_detector_identical_code()` - Drift < 0.01 for identical
2. `test_drift_detector_completely_different()` - Drift > 0.5 for unrelated
3. `test_drift_detector_minor_changes()` - Drift < 0.2 for minor syntax changes
4. `test_drift_detector_moderate_changes()` - Drift 0.2-0.3 for moderate changes
5. `test_threshold_enforcement()` - Orchestrator aborts when drift > threshold
6. `test_model_reuse()` - Verify no duplicate SentenceTransformer instantiation
7. `test_performance()` - Drift computation < 100ms per check
8. `test_config_disabled()` - Drift detection respects enabled flag
9. `test_cumulative_drift_tracking()` - Verify comparison against original, not previous
10. `test_database_drift_storage()` - Verify drift_score persisted correctly

## Critical Implementation Rules

### SAFE-WRITE PROTOCOL

1. **READ FIRST**: Read all files before editing
2. **MERGE CHANGES**: Never overwrite existing functionality
3. **PRESERVE LOGIC**: Keep all existing control flows intact
4. **TEST INCREMENTALLY**: Test after each file change

### Performance Requirements

1. **Model Reuse**: Use `self.vector_db_service._embedding_model` (already instantiated)
2. **Lazy Initialization**: Initialize DriftDetector once in orchestrator
3. **Target Latency**: < 100ms per drift computation
4. **No Blocking**: Drift check should not slow down fix loop significantly

### Drift Comparison Strategy

**CRITICAL**: Always compare fixed_code against `example.original_code`, NOT `current_code`.

**Rationale**:
- `current_code` tracks the most recent iteration
- Comparing against `current_code` only measures delta between iterations
- We need CUMULATIVE drift from original intent
- By iteration 5, cumulative drift can be 0.4 even if per-iteration drift is 0.1

### Threshold Guidance

Based on empirical testing (to be validated):
- **0.0-0.1**: Trivial (formatting, whitespace, using statements)
- **0.1-0.2**: Minor (var → type, try-catch added)
- **0.2-0.3**: Moderate (restructuring, different control flow)
- **0.3-0.5**: Significant (different APIs, altered logic)
- **0.5+**: Major drift (wrong intent, unrelated code)

**Recommended Default**: 0.3 (conservative)

## Implementation Order

1. **Create `src/services/drift_detector.py`** (30 mins)
   - Implement DriftDetector class
   - Test locally with sample code pairs

2. **Update `src/core/config.py`** (15 mins)
   - Add DriftConfig model
   - Add to GlobalConfig

3. **Update `config/global.json`** (5 mins)
   - Add drift section

4. **Update `src/core/database.py`** (30 mins)
   - Add drift columns to schema
   - Add update_snippet method
   - Test schema migration

5. **Update `src/pipeline/orchestrator.py` - Compilation** (1 hour)
   - Add drift detector initialization
   - Integrate drift check into fix loop
   - Add threshold gating
   - Test with sample family

6. **Update `src/pipeline/orchestrator.py` - Runtime** (1 hour)
   - Same pattern as compilation
   - Test with sample family

7. **Create `tests/test_drift_detector.py`** (2 hours)
   - Implement all 10 test cases
   - Run pytest suite
   - Validate performance benchmarks

8. **Integration Testing** (1 hour)
   - Run full pipeline with drift detection enabled
   - Test threshold enforcement
   - Verify database persistence

9. **Documentation and Evidence** (1 hour)
   - Create changes.md
   - Create evidence.md with test outputs
   - Create self_review.md

## Acceptance Criteria Checklist

- [ ] DriftDetector class implemented with model reuse
- [ ] DriftConfig added to config system
- [ ] drift section added to global.json
- [ ] drift_score and drift_similarity columns added to database
- [ ] update_snippet method added to Database class
- [ ] Drift detection integrated into compilation phase
- [ ] Drift detection integrated into runtime phase
- [ ] Threshold gating aborts fix loop when exceeded
- [ ] Drift scores logged to database
- [ ] 10+ unit tests pass with 100% coverage
- [ ] Performance: drift computation < 100ms per check
- [ ] Config flag enables/disables drift detection
- [ ] Comparison uses original_code (not current_code)
- [ ] No duplicate model instantiation (verified)

## Risk Analysis

**Risk 1**: Model instantiation cost
- **Mitigation**: Reuse VectorDBService._embedding_model (already instantiated)
- **Validation**: Test shows no duplicate instantiation

**Risk 2**: Drift computation adds latency to fix loop
- **Mitigation**: Target < 100ms per check (negligible vs LLM call ~5-10 seconds)
- **Validation**: Performance test in test suite

**Risk 3**: Database schema migration
- **Mitigation**: New columns allow NULL (safe to add)
- **Validation**: Test on existing database

**Risk 4**: False positives (rejecting valid fixes)
- **Mitigation**: Conservative threshold (0.3), config flag to disable
- **Validation**: Monitor stats after deployment

**Risk 5**: Integration breaks existing functionality
- **Mitigation**: SAFE-WRITE protocol, preserve all existing logic
- **Validation**: Full pipeline test with drift disabled

## Success Metrics

1. **Functionality**: All 10 tests pass
2. **Performance**: Drift computation < 100ms
3. **Safety**: No existing tests broken
4. **Observability**: Drift scores visible in database
5. **Quality**: All 12 dimensions ≥ 4/5 in self-review

## Next Steps

Proceeding to implementation phase with this plan as guide.

**Estimated Total Time**: 8-10 hours
**Target Completion**: 2026-01-17

---

**Plan Status**: ✅ APPROVED - Ready for implementation
