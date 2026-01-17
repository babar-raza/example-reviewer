# Implementation Plan: ID-04 Two-Code Final Review (Quick Win)

## Task Overview
**ID**: ID-04
**Priority**: P1 (HIGH - Quick win, prevents intent drift)
**Risk**: LOW (enhancement to existing LLM flow)
**Estimated Time**: 8 hours
**Agent**: Agent B (Implementation)

## Problem Statement
Current validation flow has a critical gap:
1. LLM fixes code
2. Code compiles successfully
3. Snippet marked as verified - DONE

**Missing Step**: No verification that the fixed code still matches the original intent!

This can lead to "verified" snippets that compile but have completely different functionality than intended.

## Solution: Stage 5.5 Final Review
Add a new stage between compilation success and verification that compares:
- Original code (intent source)
- Final fixed code (after LLM fixes)

The LLM will analyze whether the fixed code preserves the original intent.

## Implementation Strategy

### 1. Code Analysis (COMPLETED)
- Reviewed `src/services/llm_service.py` (1007 lines)
  - Has `fix_code()` method for compilation/runtime fixes
  - Has `review_markdown_structured()` for final markdown review
  - Uses OpenAI-compatible API with retry logic
  - Good structure for adding new `final_review()` method

- Reviewed `src/pipeline/orchestrator.py` (1349 lines)
  - Main pipeline in `run_full_pipeline()`
  - Compilation phase: lines 451-635
  - Runtime phase: lines 637-951
  - **Integration point**: After compilation success (lines 596-598)
  - **Integration point**: After runtime success (lines 883-907)

- Reviewed `config/global.json`
  - Has `final_review` config section (lines 63-69)
  - Already configured with basic settings
  - Need to add `confidence_threshold` and additional options

### 2. Implementation Components

#### Component A: LLM Service Enhancement
**File**: `src/services/llm_service.py`
**Action**: Add `final_review()` method

**Method Signature**:
```python
def final_review(
    self,
    original_code: str,
    fixed_code: str,
) -> Dict[str, Any]:
```

**Features**:
- Prompt includes both original and fixed code
- Returns structured JSON: `{intent_preserved, confidence, explanation, drift_details}`
- JSON validation and error handling
- Retry logic for parsing failures

#### Component B: Orchestrator Integration
**File**: `src/pipeline/orchestrator.py`
**Action**: Add Stage 5.5 after compilation succeeds

**Integration Points**:
1. **Compilation phase** (after line 598): When snippet compiled with LLM fix
2. **Runtime phase** (after line 884): When snippet passed runtime with LLM fix

**Logic Flow**:
```python
# Stage 5.5: Final Review (if enabled and code was LLM-fixed)
if global_config.final_review.enabled and fixed_code:
    review = self.llm_service.final_review(
        original_code=example.original_code,
        fixed_code=fixed_code
    )

    if not review['intent_preserved']:
        # Intent drift detected - mark as needs-fix
        self.db.update_example_status(
            example.example_id,
            ExampleStatus.NEEDS_FIX,
            failure_reason=f"Intent drift: {review['explanation']}"
        )
        # Log drift details for debugging
        self.db.log_event(...)
        continue  # Skip to next example

    # Intent preserved - continue to verification
    self.db.log_event(...)
```

#### Component C: Configuration Enhancement
**File**: `config/global.json`
**Action**: Add missing configuration options

**Config Update**:
```json
"final_review": {
  "enabled": true,
  "confidence_threshold": 0.7,
  "model": "sonnet-4.5",
  "timeout_seconds": 30,
  "auto_remediation_enabled": false,
  "max_review_attempts": 2,
  "strict_mode": false,
  "fail_on_critical": true,
  "only_review_llm_fixed": true
}
```

#### Component D: Test Suite
**File**: `tests/test_final_review.py`
**Action**: Create comprehensive test suite

**Test Cases**:
1. `test_final_review_detects_intent_drift()` - Catches functionality changes
2. `test_final_review_approves_valid_fix()` - Approves semantic equivalence
3. `test_final_review_handles_missing_functionality()` - Detects removed features
4. `test_final_review_json_parsing()` - Tests response validation
5. `test_final_review_integration()` - End-to-end pipeline test
6. `test_final_review_disabled()` - Tests config disable flag
7. `test_final_review_confidence_threshold()` - Tests threshold filtering

### 3. Database Considerations
The orchestrator already uses `ExampleStatus` enum. Need to check if we need a new status:
- Option 1: Use existing `NEEDS_FIX` status with failure_reason
- Option 2: Add new `INTENT_DRIFT_DETECTED` status (requires models.py update)

**Decision**: Use existing `NEEDS_FIX` status to avoid schema changes (quick win).

### 4. Prompt Design
The final review prompt must:
- Clearly present both original and fixed code
- Define "intent preservation" vs "intent drift"
- Request structured JSON response
- Include drift_details array for debugging

**Key Guidelines**:
- Be strict: If unsure, mark as intent_preserved=false
- Focus on semantic equivalence, not syntactic similarity
- Minor syntax changes (e.g., adding `using` statements) are OK
- Major functionality changes (e.g., extract instead of create) are NOT OK

### 5. Integration Considerations

#### When to Run Final Review?
- Only after **LLM fixes** (not for code that compiled on first try)
- Only when `final_review.enabled=true` in config
- Only when `confidence >= confidence_threshold`

#### What to Do on Intent Drift?
- Mark example as `NEEDS_FIX`
- Log drift explanation to database
- Store drift_details for manual review
- Continue to next example (don't block pipeline)

#### Performance Impact
- Low: Only runs for LLM-fixed examples (small percentage)
- Typical: 1-3 seconds per review
- Cost: Single LLM call per fixed example

### 6. Success Criteria
- [ ] `final_review()` method added to LLMService
- [ ] Stage 5.5 integrated in orchestrator after compilation
- [ ] Prompt includes both original and fixed code
- [ ] LLM response parsed and validated (JSON schema)
- [ ] Intent drift detected → snippet marked NEEDS_FIX
- [ ] Intent preserved → snippet continues to verification
- [ ] Drift details logged to database
- [ ] Config option to enable/disable final review
- [ ] Unit tests pass: `pytest tests/test_final_review.py -v`
- [ ] Integration test verifies end-to-end flow

## Implementation Order
1. ✅ Create output directory and plan
2. ⏳ Implement `final_review()` method in llm_service.py
3. ⏳ Integrate Stage 5.5 in orchestrator.py (compilation phase)
4. ⏳ Integrate Stage 5.5 in orchestrator.py (runtime phase)
5. ⏳ Update config/global.json with additional options
6. ⏳ Create comprehensive test suite
7. ⏳ Run tests and verify functionality
8. ⏳ Generate deliverables (changes.md, evidence.md, self_review.md)

## Risk Mitigation
- **Risk**: JSON parsing failures from LLM
  - **Mitigation**: Try/except with fallback, retry logic

- **Risk**: False positives (marking good fixes as drift)
  - **Mitigation**: Confidence threshold, conservative prompt design

- **Risk**: Performance impact
  - **Mitigation**: Only run on LLM-fixed examples, configurable enable/disable

## Expected Impact
- **Benefit**: Prevents false positives (verified snippets with wrong functionality)
- **Benefit**: Catches cases where LLM "fixes" by changing behavior
- **Benefit**: Low cost (only runs after compilation succeeds)
- **Cost**: ~1-3 seconds per LLM-fixed example
- **Value**: High (prevents incorrect documentation from being published)

## Notes
- This is a "quick win" - minimal changes to existing codebase
- Leverages existing LLM service infrastructure
- Uses existing database schema (no migrations needed)
- Config already has `final_review` section - just needs enhancement
- No breaking changes to existing pipeline flow
