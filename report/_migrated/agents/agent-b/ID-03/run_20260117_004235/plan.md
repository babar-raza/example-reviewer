# Implementation Plan: ID-03 - Original-Anchored Fix Prompts

**Agent:** Agent B (Implementation Specialist)
**Task:** ID-03 - Original-Anchored Fix Prompts
**Priority:** P2 (MEDIUM)
**Estimated Time:** 6 hours
**Run Folder:** `c:/Users/prora/OneDrive/Documents/GitHub/example-reviewer/reports/agents/agent-b/ID-03/run_20260117_004235/`

## Objective

Reduce drift generation at the source by anchoring LLM fix prompts to the original code. This will help the LLM make minimal changes that preserve the teaching intent of the original examples.

**Expected Impact:** 20-30% reduction in semantic drift for LLM-generated fixes.

## Current State Analysis

### Existing Code Structure

1. **`src/services/llm_service.py`:**
   - `fix_code()` method (lines 278-320) - Main entry point for fixes
   - `_fix_compile_code()` (lines 351-482) - Compilation fix handler
   - `_fix_runtime_code()` (lines 484-601) - Runtime fix handler
   - Current parameters: code, error_logs, context_type, api_context, similar_examples, test_data_info, family_config, scaffolding_hints, section_heading, description_context, topic
   - **MISSING:** `original_code` parameter

2. **`src/services/compilation_service.py`:**
   - Creates `LLMFixPayload` (lines 599-655)
   - Calls `llm_service.fix_code()` in orchestrator (needs checking)
   - **Has access to:** `example.original_code` via ExampleRecord

3. **`src/services/runtime_service.py`:**
   - Similar structure to compilation_service
   - Calls `llm_service.fix_code()` for runtime fixes
   - **Has access to:** `example.original_code` via ExampleRecord

4. **`src/core/models.py`:**
   - `ExampleRecord` has `original_code` field (line 86)
   - `ExampleRecord` has `compilable_code` field (line 87)
   - `ExampleRecord` has `verified_code` field (line 88)

### Current Prompt Structure

**Compilation prompts:**
- System prompt: Focuses on minimal changes, CRITICAL RULES
- Includes: code, errors, API context, similar examples, scaffolding hints
- Has topic context for minimal-change guidance
- **Missing:** Original code reference, explicit scope creep examples

**Runtime prompts:**
- Similar structure to compilation
- Includes test data info
- **Missing:** Original code reference, explicit scope creep examples

## Implementation Plan

### Phase 1: Update LLM Service (Core Changes)

**File:** `src/services/llm_service.py`

1. **Update `fix_code()` signature (line 278):**
   - Add `original_code: Optional[str] = None` parameter
   - This is the main entry point, must be backward compatible

2. **Update `_fix_compile_code()` signature (line 351):**
   - Add `original_code: Optional[str] = None` parameter
   - Pass through from `fix_code()`

3. **Update `_fix_runtime_code()` signature (line 484):**
   - Add `original_code: Optional[str] = None` parameter
   - Pass through from `fix_code()`

4. **Enhance compilation prompt (lines 363-482):**
   - Add original code section (only if original differs from current)
   - Add fix instructions section (always)
   - Add BAD fixes examples (scope creep)
   - Add GOOD fixes examples (minimal)
   - Integrate with existing prompt structure

5. **Enhance runtime prompt (lines 496-601):**
   - Same enhancements as compilation prompt
   - Adapt for runtime context

### Phase 2: Update Compilation Service

**File:** `src/services/compilation_service.py`

1. **Find orchestrator call to `llm_service.fix_code()`:**
   - Search codebase for where compilation_service calls fix_code()
   - Add `original_code=example.original_code` parameter

2. **Ensure original_code is passed through:**
   - Verify example.original_code is accessible
   - Pass to LLM service

### Phase 3: Update Runtime Service

**File:** `src/services/runtime_service.py`

1. **Find orchestrator call to `llm_service.fix_code()`:**
   - Search codebase for where runtime_service calls fix_code()
   - Add `original_code=example.original_code` parameter

2. **Ensure original_code is passed through:**
   - Verify example.original_code is accessible
   - Pass to LLM service

### Phase 4: Create Comprehensive Test Suite

**File:** `tests/test_anchored_prompts.py`

**Test Categories:**

1. **Prompt Structure Tests (5 tests):**
   - test_fix_prompt_includes_original_code_section
   - test_fix_prompt_includes_minimal_change_instruction
   - test_fix_prompt_includes_intent_preservation_emphasis
   - test_fix_prompt_includes_scope_creep_examples
   - test_fix_prompt_includes_good_fix_examples

2. **Conditional Logic Tests (3 tests):**
   - test_original_code_not_included_if_identical
   - test_original_code_not_included_if_none
   - test_original_code_included_if_different

3. **Integration Tests (4 tests):**
   - test_compilation_service_passes_original_code
   - test_runtime_service_passes_original_code
   - test_fix_code_accepts_original_code_parameter
   - test_backward_compatibility_without_original_code

4. **Validation Tests (3 tests):**
   - test_prompt_structure_valid
   - test_csharp_code_blocks_properly_formatted
   - test_prompt_sections_in_correct_order

5. **Edge Cases (2 tests):**
   - test_empty_original_code
   - test_very_long_original_code

**Total: 17 tests**

### Phase 5: Quality Assurance

1. Run all tests: `pytest tests/test_anchored_prompts.py -v`
2. Run integration test: `python -m src.cli.main run --family zip --max-examples 5`
3. Verify prompts in logs contain all required sections
4. Check backward compatibility with existing code
5. Perform self-review against 12 quality dimensions

## Prompt Structure Design

### Original Code Section (Conditional)

```
## Original Code (teaching intent reference):
```csharp
{original_code}
```

**CRITICAL**: The original code demonstrates a specific concept/feature.
Your fix MUST preserve this teaching intent.
Do NOT add features, error handling, or complexity beyond what's needed to make it compile/run.
```

**Condition:** Only include if `original_code` is provided AND differs from current `code`

### Fix Instructions Section (Always)

```
## Fix Instructions:
1. **Minimal Changes**: Make ONLY the changes needed to fix the errors
2. **Preserve Intent**: The fixed code must demonstrate the SAME concept as the original
3. **No Scope Creep**: Do NOT add error handling, validation, or features not in the original
4. **Teaching Clarity**: A reader should understand the same lesson from your fix
```

### BAD Fixes Examples (Always)

```
## Examples of BAD fixes (scope creep):
❌ Adding try-catch blocks when original had none
❌ Adding File.Exists() checks when original assumed file exists
❌ Adding complex error messages when original used simple code
❌ Restructuring code into methods when original was inline
```

### GOOD Fixes Examples (Always)

```
## Examples of GOOD fixes (minimal):
✅ Adding missing using statement
✅ Fixing typo in variable name
✅ Correcting API method signature
✅ Adding namespace qualification
```

## Implementation Order

1. **Read all files** - Understand current implementation
2. **Update llm_service.py** - Core prompt changes
3. **Check orchestrator** - Find where services call fix_code()
4. **Update compilation_service** - Pass original_code
5. **Update runtime_service** - Pass original_code
6. **Create test file** - Comprehensive coverage
7. **Run tests** - Verify all pass
8. **Manual validation** - Run pipeline on real data
9. **Document changes** - Create changes.md and evidence.md
10. **Self-review** - Quality assessment

## Success Criteria Checklist

- [ ] fix_code() accepts original_code parameter (backward compatible)
- [ ] Prompts include original code section when original differs from current
- [ ] Prompts include minimal change instruction
- [ ] Prompts include intent preservation emphasis
- [ ] Prompts include scope creep examples (bad fixes)
- [ ] Prompts include minimal fix examples (good fixes)
- [ ] compilation_service passes original_code to LLM
- [ ] runtime_service passes original_code to LLM
- [ ] All tests pass (17+ tests)
- [ ] Quality score ≥ 48/60 (all dimensions ≥ 4/5)
- [ ] No breaking changes
- [ ] Backward compatible (original_code optional)

## Risk Mitigation

1. **Backward Compatibility:** Make original_code optional with default=None
2. **Prompt Length:** Keep examples concise to avoid token limits
3. **Conditional Logic:** Test thoroughly to ensure original code only shown when different
4. **Integration:** Find all call sites in orchestrator to ensure consistent usage
5. **Testing:** Mock LLM responses to avoid network dependencies

## Timeline

- Phase 1: 1.5 hours (LLM service updates)
- Phase 2: 0.5 hours (Compilation service updates)
- Phase 3: 0.5 hours (Runtime service updates)
- Phase 4: 2 hours (Test suite creation)
- Phase 5: 1.5 hours (QA and documentation)

**Total:** 6 hours

## Next Steps

1. Find orchestrator file to understand call patterns
2. Implement Phase 1 (LLM service core changes)
3. Implement Phase 2-3 (Service integrations)
4. Implement Phase 4 (Test suite)
5. Implement Phase 5 (QA)
