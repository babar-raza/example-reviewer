# Intent Drift Prevention Healing Plan

## Context
**Critical Issue Identified in `reviews/claude.md`:**

The pipeline suffers from **cumulative intent drift** during multi-phase LLM fixing. Code examples that go through compilation fixes (up to 3 retries) + runtime fixes (up to 3 retries) can evolve far from their original teaching purpose. By the final phase, examples may be technically correct but pedagogically misleading.

**Root Causes:**
1. **Cumulative Drift**: Up to 6 LLM transformations (3 compile + 3 runtime) stack changes
2. **No Drift Guard**: Cascading degradation check only prevents build errors, not semantic drift
3. **Execution-First Prompts**: LLMs naturally expand code to make it work (add error handling, file checks, etc.)
4. **Context-Blind Final Review**: Phase E sees only final code vs markdown, not original → verified delta
5. **Polluted Vector DB**: Fixed examples propagate drift patterns to future fixes

**Business Impact:**
- Documentation examples become misleading teaching material
- Users copy complex code when simple patterns were intended
- Trust in documentation erodes
- Manual review required to catch semantic drift

**Reference:** See `reviews/claude.md` for detailed diagnostic

## Gap → Taskcard Mapping

| Gap/Blocker ID | Description | Taskcard ID(s) |
|----------------|-------------|----------------|
| ID-GAP-01 | No semantic similarity tracking between original and fixed code | ID-01 |
| ID-GAP-02 | No drift threshold gate to reject over-modified fixes | ID-02 |
| ID-GAP-03 | Fix prompts don't anchor to original code intent | ID-03 |
| ID-GAP-04 | Final review sees only current code, not original vs verified comparison | ID-04 |
| ID-GAP-05 | Vector DB stores drifted examples, causing contagion | ID-05 |
| ID-GAP-06 | No observability into drift metrics (which examples drifted, by how much) | ID-01, ID-06 |

---

## Repo Reality Check

**Purpose**: Verify pipeline phases and LLM integration before implementing drift prevention.

### Validation Commands

```bash
# 1. Verify Phase E final review exists
grep -n "def _run_final_review_phase" src/pipeline/orchestrator.py

# 2. Verify LLM service review method
grep -n "def review_markdown_structured" src/services/llm_service.py

# 3. Check compilation fix method (where drift accumulates)
grep -n "def fix_code" src/services/llm_service.py

# 4. Verify cascading degradation check exists (plan mentions it)
grep -n "cascading.*degradation\|prevent.*worse" src/pipeline/orchestrator.py

# 5. Check vector DB service (for drift contagion prevention)
[ -f src/services/vector_db_service.py ] && echo "EXISTS: VectorDBService" || echo "MISSING"
grep -n "class VectorDBService\|def add_example\|embedding_model" src/services/vector_db_service.py

# 6. Verify example_records table has original_code field
grep -n "original_code" src/core/models.py
grep -n "original_code" src/core/database.py

# 7. Check if sentence-transformers is available for drift scoring
grep "sentence-transformers" requirements.txt
```

### Reality Check Results

| Assumption | Status | Evidence |
|------------|--------|----------|
| Phase E final review exists | ✅ **CORRECT** | `_run_final_review_phase()` in orchestrator.py |
| LLM fix_code method exists | ✅ **CORRECT** | Used for compilation and runtime fixes |
| Cascading degradation check exists | ✅ **CORRECT** | Lines 910-922 in orchestrator.py (per claude.md) |
| Vector DB integration exists | ✅ **CORRECT** | VectorDBService in services/vector_db_service.py |
| original_code field exists | ⚠️ **VERIFY** | Need to confirm ExampleRecord stores original |
| sentence-transformers available | ✅ **CORRECT** | Used by VectorDBService for embeddings |
| Up to 6 LLM transforms possible | ✅ **CORRECT** | 3 compile retries + 3 runtime retries max |

### ChatGPT Review Suggestions

**From reviews/chatgpt.md**:
1. ✅ **ID-04 first is correct** - Two-code review is low-risk and immediately increases correctness
2. ⚠️ **Drift metric implementation** - Reuse VectorDBService embedding model (don't instantiate new `SentenceTransformer()`)
3. ⚠️ **Drift computed against original_code** - Not just previous attempt, to preserve teaching intent
4. ✅ **Vector DB contamination** - Selective storage with exclude_high_drift option is good

### Go/No-Go Decision

✅ **GO** - Plan is strategically sound and matches repository structure.

**Enhancements to Incorporate**:
- **ID-01**: Reuse `VectorDBService` embedding model instance instead of creating new `SentenceTransformer()`
- **ID-01**: Explicitly compute drift against `original_code` (teaching intent), not just previous attempt
- **ID-05**: Add acceptance check: "search results never return examples above drift threshold when `exclude_high_drift=true`"
- **ID-01**: Add note about cost of `SentenceTransformer()` instantiation (memory + CPU intensive)

**Estimated Reality Check Time**: 12 minutes

---

## Taskcard ID-04: Two-Code Final Review (Quick Win)

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-04 (Final review lacks original context)

**Priority:** 🔥 **HIGH** - Immediate improvement, low risk, fast to implement

**Role:** Senior engineer delivering context-aware final review for intent preservation.

### Scope

**Fix:**
- Modify `_run_final_review_phase()` to include both `original_code` AND `verified_code`
- Update `LLMService.review_markdown_structured()` prompt to compare original vs verified
- Add explicit evaluation criteria: "Does verified code preserve teaching intent of original?"
- Track intent preservation assessment in review results
- Log examples where intent diverged significantly

**Allowed paths:**
- `src/pipeline/orchestrator.py` - update `_run_final_review_phase()`
- `src/services/llm_service.py` - update `review_markdown_structured()` prompt
- `src/core/models.py` - add `intent_preserved` field to ReviewResult
- `tests/test_final_review.py` - new test file for two-code review

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli run --family zip --max-examples 10`
- Verify Phase E logs show "Two-code review: original vs verified"
- Check review results for `intent_preserved` assessment
- Run with examples known to drift (complex runtime fixes)
- Verify reviewer identifies drift: "Current code adds unrelated features"

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_final_review.py -v` passes
- Test two-code review prompt includes original and verified
- Test reviewer identifies intent divergence correctly
- Test reviewer approves minimal changes
- Test intent_preserved field stored in database

**Config respected end-to-end:**
- Final review uses two-code comparison by default
- Original code always included in review context

**No mock data in production paths:**
- Real LLM review with both code versions
- Mock LLM responses in tests

### Deliverables

1. **Updated `src/pipeline/orchestrator.py` - `_run_final_review_phase()`:**
   ```python
   def _run_final_review_phase(self, family: str) -> Dict[str, Any]:
       """
       Run Phase E: Final LLM Review with two-code comparison.

       NEW: Includes both original_code and verified_code for intent preservation check.
       """
       # ... existing setup ...

       for file_path, file_examples in files.items():
           # ... existing file reading ...

           # Build snippets with BOTH original and verified code
           snippets = [
               {
                   'original_code': e.original_code,
                   'verified_code': e.verified_code or e.compilable_code or e.original_code,
                   'example_id': e.example_id,
                   'line': e.location.start_line,
                   'language': e.language,
                   'section_heading': e.section_heading,
                   'has_fixes': bool(e.verified_code),  # Flag if code was modified
               }
               for e in file_examples
           ]

           # Call two-code consensus review
           review_result = self._consensus_review_with_intent(
               content, snippets
           )

           # ... store results with intent_preserved field ...
   ```

2. **Updated `src/services/llm_service.py` - `review_markdown_structured()`:**
   - Add new method `review_markdown_with_intent()`:
     ```python
     def review_markdown_with_intent(
         self,
         content: str,
         snippets: List[Dict[str, Any]]
     ) -> Dict[str, Any]:
         """
         Review markdown with two-code comparison for intent preservation.

         Args:
             content: Full markdown content
             snippets: List of dicts with 'original_code', 'verified_code', 'has_fixes', etc.

         Returns:
             Review result with 'approved', 'issues', 'intent_preserved' fields
         """
         # Build prompt with original vs verified comparison
         prompt_parts = [
             "You are reviewing code examples in technical documentation.",
             "CRITICAL: Some examples were modified by an automated system to fix compilation/runtime errors.",
             "Your task: Verify the modified examples still teach the SAME concept as the originals.",
             "",
             "# Evaluation Criteria (in order of importance):",
             "1. **Intent Preservation**: Does the verified code demonstrate the same concept/feature as the original?",
             "2. **Teaching Clarity**: Would a reader understand the intended lesson from the verified code?",
             "3. **Scope Creep**: Did fixes add unrelated features (error handling, validation, complex logic)?",
             "4. **Code Bloat**: Is the verified code significantly longer/more complex than needed?",
             "",
             "# Examples to Review:",
             ""
         ]

         for i, snippet in enumerate(snippets):
             has_fixes = snippet.get('has_fixes', False)
             prompt_parts.append(f"## Example {i+1} (Line {snippet['line']})")

             if snippet.get('section_heading'):
                 prompt_parts.append(f"**Section**: {snippet['section_heading']}")

             if has_fixes:
                 prompt_parts.append("### Original Code (before fixes):")
                 prompt_parts.append(f"```{snippet['language']}")
                 prompt_parts.append(snippet['original_code'])
                 prompt_parts.append("```")
                 prompt_parts.append("")
                 prompt_parts.append("### Verified Code (after fixes):")
                 prompt_parts.append(f"```{snippet['language']}")
                 prompt_parts.append(snippet['verified_code'])
                 prompt_parts.append("```")
                 prompt_parts.append("")
                 prompt_parts.append("**Question**: Does the verified code preserve the teaching intent of the original?")
             else:
                 prompt_parts.append("### Code (unchanged):")
                 prompt_parts.append(f"```{snippet['language']}")
                 prompt_parts.append(snippet['verified_code'])
                 prompt_parts.append("```")
                 prompt_parts.append("(No fixes applied - verify code matches documentation)")

             prompt_parts.append("")

         prompt_parts.extend([
             "",
             "# Response Format:",
             "Respond with JSON:",
             "{",
             '  "approved": true/false,',
             '  "intent_preserved": true/false,  // NEW: Overall intent preservation',
             '  "issues": [',
             '    {',
             '      "example_id": "...",',
             '      "issue_type": "intent_drift|scope_creep|code_bloat|...",',
             '      "severity": "critical|warning|info",',
             '      "description": "...",',
             '      "suggestion": "..."',
             '    }',
             '  ]',
             '}',
             '',
             '**IMPORTANT**: Flag "intent_drift" if verified code teaches a different concept than original.',
             'Flag "scope_creep" if verified code adds features beyond the original intent.',
             'Flag "code_bloat" if verified code is unnecessarily complex vs original.',
             'Approve ONLY if intent is preserved and code teaches the intended concept clearly.'
         ])

         full_prompt = '\n'.join(prompt_parts)

         # Call LLM with structured output
         response = self._call_with_structured_output(
             prompt=full_prompt,
             response_schema={
                 "type": "object",
                 "properties": {
                     "approved": {"type": "boolean"},
                     "intent_preserved": {"type": "boolean"},
                     "issues": {
                         "type": "array",
                         "items": {
                             "type": "object",
                             "properties": {
                                 "example_id": {"type": "string"},
                                 "issue_type": {"type": "string"},
                                 "severity": {"type": "string"},
                                 "description": {"type": "string"},
                                 "suggestion": {"type": "string"}
                             }
                         }
                     }
                 }
             }
         )

         return {
             'approved': response.get('approved', False),
             'intent_preserved': response.get('intent_preserved', True),
             'issues': response.get('issues', []),
             'raw_response': response
         }
     ```

3. **Updated `src/core/models.py` - ReviewResult:**
   ```python
   @dataclass
   class ReviewResult:
       """Result of final LLM review with intent preservation tracking."""
       review_id: str = field(default_factory=lambda: generate_id("review"))
       file_path: str = ""
       run_id: str = ""
       family: str = ""
       approved: bool = False
       intent_preserved: bool = True  # NEW: Intent preservation assessment
       review_attempt: int = 1
       issues: List[ReviewIssue] = field(default_factory=list)
       llm_response: str = ""
       created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
   ```

4. **Updated database schema (if needed):**
   ```sql
   ALTER TABLE review_results ADD COLUMN intent_preserved BOOLEAN DEFAULT 1;
   ```

5. **New test file `tests/test_final_review.py`:**
   - `test_two_code_review_includes_original_and_verified`
   - `test_reviewer_identifies_intent_drift`
   - `test_reviewer_identifies_scope_creep`
   - `test_reviewer_identifies_code_bloat`
   - `test_reviewer_approves_minimal_changes`
   - `test_intent_preserved_field_stored`
   - `test_unchanged_examples_reviewed_normally`

6. **Forward-compatible migration:**
   - Existing review flow enhanced with two-code comparison
   - Examples without fixes use single-code review path
   - intent_preserved defaults to True for backward compatibility

### Hard Rules

- ✅ Keep public signatures: Enhanced review, not breaking changes
- ✅ No network in offline tests: Mock LLM responses
- ✅ Deterministic runs: Same code + fixes → same review
- ✅ No new deps: Use existing LLM service
- ✅ Keep code/docs/tests in sync: Document two-code review format

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Two-code comparison works; intent assessment accurate; issues categorized correctly |
| **Completeness** | Both original and verified included; intent criteria clear; intent_preserved tracked |
| **Robustness** | Handles unchanged examples; handles heavily modified examples; graceful degradation |
| **Testability** | Tests verify intent detection; tests cover drift scenarios; tests verify storage |
| **Documentation** | Two-code review format documented; intent criteria explained; examples provided |
| **Integration** | Works with existing consensus review; backward compatible; enhances Phase E |

### Now (Runbook)

```bash
# 1. Update ReviewResult model to add intent_preserved field
# Edit src/core/models.py, add field to ReviewResult dataclass

# 2. Add database migration for intent_preserved column (if needed)
# Check if database schema update required

# 3. Create review_markdown_with_intent() method in LLMService
# Add after review_markdown_structured() around line 400

# 4. Update _run_final_review_phase() to build two-code snippets
# Edit src/pipeline/orchestrator.py around line 1080
# Change snippet structure to include original_code, verified_code, has_fixes

# 5. Update _consensus_review() to call new review method
# Pass snippets with two-code structure

# 6. Create test file tests/test_final_review.py
# Test intent drift detection, scope creep, code bloat scenarios

# 7. Run tests
pytest tests/test_final_review.py -v

# 8. Integration test with examples known to drift
# Use examples with complex runtime fixes
# Verify reviewer identifies drift

# 9. Review outputs - check for intent_preserved field
# Verify database stores intent_preserved correctly

# 10. Check logs for "intent_drift" issues flagged
# Verify intent preservation assessment appears in review results
```

---

## Taskcard ID-02: Drift Threshold Gate

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-02 (No drift threshold gate)

**Priority:** 🔥 **HIGH** - Prevents bad fixes from propagating

**Role:** Senior engineer delivering drift prevention gate for fix quality control.

### Scope

**Fix:**
- Add `max_drift_score` threshold configuration (default 0.4)
- Reject fixes where semantic drift exceeds threshold
- Compute drift score after each LLM fix attempt
- Track drift scores in attempt metadata for observability
- Configure per-family drift tolerance

**Allowed paths:**
- `src/services/compilation_service.py` - add drift gate to compile fixes
- `src/services/runtime_service.py` - add drift gate to runtime fixes
- `src/core/config.py` - add drift threshold config
- `config/families/zip.json` - example drift threshold
- `config/global.json` - default drift threshold
- `tests/test_drift_gate.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Add to `config/global.json`:
  ```json
  {
    "drift_prevention": {
      "enabled": true,
      "max_drift_score": 0.4,
      "drift_metric": "semantic_similarity"
    }
  }
  ```
- Run `python -m cli run --family zip`
- Verify fixes with high drift score are rejected
- Check logs: "Fix rejected: drift_score=0.52 exceeds threshold 0.4"
- Verify examples with rejected fixes stay in COMPILE_FAILED or RUNTIME_FAILED status

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_drift_gate.py -v` passes
- Test drift score computed after fix
- Test fix rejected when drift > threshold
- Test fix accepted when drift < threshold
- Test drift scores stored in attempts table
- Test drift threshold configurable per family

**Config respected end-to-end:**
- Drift gate enabled/disabled via config
- Threshold configurable
- Per-family overrides work

**No mock data in production paths:**
- Real drift computation on production code
- Mock LLM responses and drift scores in tests

### Deliverables

1. **Updated `src/core/config.py` - add DriftPreventionConfig:**
   ```python
   @dataclass
   class DriftPreventionConfig:
       """Configuration for intent drift prevention."""
       enabled: bool = True
       max_drift_score: float = 0.4  # 0.0 = identical, 1.0 = completely different
       drift_metric: str = "semantic_similarity"  # or "edit_distance", "token_overlap"

       def compute_drift_score(self, original: str, modified: str) -> float:
           """
           Compute semantic drift score between original and modified code.

           Returns:
               Float in [0.0, 1.0] where 0.0 = identical, 1.0 = completely different
           """
           if self.drift_metric == "semantic_similarity":
               return self._semantic_similarity_drift(original, modified)
           elif self.drift_metric == "edit_distance":
               return self._edit_distance_drift(original, modified)
           elif self.drift_metric == "token_overlap":
               return self._token_overlap_drift(original, modified)
           else:
               logger.warning(f"Unknown drift metric: {self.drift_metric}, using semantic_similarity")
               return self._semantic_similarity_drift(original, modified)

       def _semantic_similarity_drift(self, original: str, modified: str) -> float:
           """Compute drift using semantic embeddings (requires vector DB)."""
           # Use sentence-transformers embeddings
           from sentence_transformers import SentenceTransformer
           import numpy as np

           model = SentenceTransformer('all-MiniLM-L6-v2')

           # Generate embeddings
           orig_embedding = model.encode(original, convert_to_numpy=True)
           mod_embedding = model.encode(modified, convert_to_numpy=True)

           # Compute cosine similarity
           similarity = np.dot(orig_embedding, mod_embedding) / (
               np.linalg.norm(orig_embedding) * np.linalg.norm(mod_embedding)
           )

           # Convert similarity [0,1] to drift [0,1] (inverted)
           drift = 1.0 - similarity
           return float(drift)

       def _edit_distance_drift(self, original: str, modified: str) -> float:
           """Compute drift using normalized Levenshtein distance."""
           import difflib

           # Compute edit distance ratio (0.0 = completely different, 1.0 = identical)
           ratio = difflib.SequenceMatcher(None, original, modified).ratio()

           # Convert to drift (inverted)
           drift = 1.0 - ratio
           return drift

       def _token_overlap_drift(self, original: str, modified: str) -> float:
           """Compute drift using token overlap (Jaccard distance)."""
           import re

           # Tokenize (simple whitespace + punctuation split)
           orig_tokens = set(re.findall(r'\w+', original.lower()))
           mod_tokens = set(re.findall(r'\w+', modified.lower()))

           # Jaccard similarity
           intersection = len(orig_tokens & mod_tokens)
           union = len(orig_tokens | mod_tokens)

           if union == 0:
               return 0.0

           similarity = intersection / union

           # Convert to drift
           drift = 1.0 - similarity
           return drift
   ```
   - Add `drift_prevention: DriftPreventionConfig` to GlobalConfig
   - Add optional `drift_prevention: Optional[DriftPreventionConfig]` to FamilyConfig

2. **Updated `config/global.json`:**
   ```json
   {
     "drift_prevention": {
       "enabled": true,
       "max_drift_score": 0.4,
       "drift_metric": "semantic_similarity"
     },
     ...
   }
   ```

3. **Updated `src/services/compilation_service.py`:**
   ```python
   def compile_example(
       self,
       example: ExampleRecord,
       family_config: FamilyConfig,
       global_config: Optional[GlobalConfig] = None
   ) -> Tuple[bool, CompilationResult]:
       # ... existing compilation logic ...

       # After LLM fix attempt, check drift
       if global_config and global_config.drift_prevention.enabled:
           drift_config = family_config.drift_prevention or global_config.drift_prevention

           drift_score = drift_config.compute_drift_score(
               example.original_code,
               fixed_code
           )

           logger.info(f"Drift score for {example.example_id}: {drift_score:.3f}")

           # Store drift score in attempt metadata
           attempt_metadata = {
               'drift_score': drift_score,
               'drift_threshold': drift_config.max_drift_score,
               'drift_metric': drift_config.drift_metric
           }

           # Check threshold
           if drift_score > drift_config.max_drift_score:
               logger.warning(
                   f"Fix rejected for {example.example_id}: "
                   f"drift_score={drift_score:.3f} exceeds threshold {drift_config.max_drift_score}"
               )
               # Record rejected attempt
               self.record_attempt(
                   example.example_id,
                   result,
                   example.original_code,
                   None,  # No fixed code accepted
                   prompt,
                   llm_response,
                   metadata={'drift_rejected': True, **attempt_metadata}
               )
               continue  # Try next fix attempt

           # Accept fix
           self.record_attempt(
               example.example_id,
               result,
               example.original_code,
               fixed_code,
               prompt,
               llm_response,
               metadata=attempt_metadata
           )
   ```

4. **Updated `src/services/runtime_service.py`:**
   - Similar drift gate logic for runtime fixes
   - Check drift score after each LLM runtime fix

5. **New test file `tests/test_drift_gate.py`:**
   - `test_drift_score_computed_after_fix`
   - `test_fix_rejected_when_drift_exceeds_threshold`
   - `test_fix_accepted_when_drift_below_threshold`
   - `test_drift_scores_stored_in_attempts`
   - `test_drift_gate_disabled_accepts_all`
   - `test_different_drift_metrics`
   - `test_per_family_drift_threshold`

6. **Forward-compatible migration:**
   - Drift prevention disabled by default (opt-in for safety)
   - Existing fix flow unchanged unless drift prevention enabled

### Hard Rules

- ✅ Keep public signatures: Add optional global_config parameter with default
- ✅ No network in offline tests: Mock drift score computation
- ✅ Deterministic runs: Same code → same drift score
- ✅ No new deps: sentence-transformers already used for vector DB
- ✅ Keep code/docs/tests in sync: Document drift metrics and thresholds

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Drift scores accurate; threshold gate works; rejection logic correct |
| **Completeness** | Multiple drift metrics; configurable threshold; per-family overrides; metadata tracked |
| **Robustness** | Handles edge cases (empty code, identical code); graceful fallback on errors |
| **Testability** | Tests verify all drift metrics; tests verify gate logic; tests verify storage |
| **Documentation** | Drift metrics explained; threshold tuning guide; examples of good/bad drift |
| **Integration** | Works with compilation and runtime services; observability via attempts table |

### Now (Runbook)

```bash
# 1. Create DriftPreventionConfig in src/core/config.py
# Implement three drift metrics: semantic_similarity, edit_distance, token_overlap

# 2. Add drift_prevention to GlobalConfig and FamilyConfig

# 3. Update config/global.json with drift_prevention section

# 4. Update CompilationService.compile_example() to check drift
# Add drift gate after LLM fix, before accepting fix

# 5. Update RuntimeService.execute_example() to check drift
# Add drift gate after runtime fix

# 6. Update record_attempt() calls to include drift metadata
# Store drift_score, drift_threshold, drift_metric in attempts

# 7. Create test file tests/test_drift_gate.py
# Test all drift metrics and gate logic

# 8. Run tests
pytest tests/test_drift_gate.py -v

# 9. Integration test with high-drift fixes
# Create examples that cause significant code expansion
# Verify drift gate rejects high-drift fixes

# 10. Tune threshold based on real data
# Run pipeline, analyze drift scores
# Adjust max_drift_score threshold
```

---

## Taskcard ID-03: Original-Anchored Fix Prompts

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-03 (Fix prompts don't anchor to original intent)

**Priority:** 🟡 **MEDIUM** - Reduces drift generation at source

**Role:** Senior engineer delivering intent-preserving LLM prompts for minimal fixes.

### Scope

**Fix:**
- Include `original_code` in all compilation and runtime fix prompts
- Add explicit "minimal change" instruction with original as reference point
- Emphasize "preserve teaching intent" in prompts
- Provide negative examples of scope creep
- Track whether fixes reference original code in responses

**Allowed paths:**
- `src/services/llm_service.py` - update fix_code() prompt
- `src/services/compilation_service.py` - pass original code to LLM
- `src/services/runtime_service.py` - pass original code to LLM
- `tests/test_anchored_prompts.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli run --family zip --max-examples 10`
- Check LLM fix prompts include "## Original Code (for reference)"
- Verify prompts include "preserve teaching intent of original"
- Compare fixes with/without anchored prompts
- Measure drift reduction (expect 20-30% improvement)

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_anchored_prompts.py -v` passes
- Test fix prompts include original code section
- Test fix prompts include minimal change instruction
- Test fix prompts emphasize intent preservation
- Test LLM responses reference original code

**Config respected end-to-end:**
- Anchored prompts used for all LLM fixes
- Original code always included in fix context

**No mock data in production paths:**
- Real LLM prompts with original code
- Mock LLM responses in tests

### Deliverables

1. **Updated `src/services/llm_service.py` - `fix_code()` method:**
   ```python
   def fix_code(
       self,
       code: str,
       error_logs: str,
       context_type: str = "compile",
       api_context: Optional[str] = None,
       similar_examples: Optional[List[str]] = None,
       scaffolding_hints: Optional[str] = None,
       family_config: Optional[FamilyConfig] = None,
       section_heading: Optional[str] = None,
       description_context: Optional[str] = None,
       topic: Optional[str] = None,
       original_code: Optional[str] = None  # NEW: Original code before any fixes
   ) -> LLMResponse:
       """
       Fix code with LLM, anchored to original intent.

       NEW: Includes original_code for intent preservation.
       """
       # Build prompt with original code anchor
       prompt_parts = [
           f"You are fixing {context_type} errors in C# code examples from technical documentation.",
           ""
       ]

       # Add original code section (NEW)
       if original_code and original_code != code:
           prompt_parts.extend([
               "## Original Code (teaching intent reference):",
               "```csharp",
               original_code,
               "```",
               "",
               "**CRITICAL**: The original code demonstrates a specific concept/feature.",
               "Your fix MUST preserve this teaching intent.",
               "Do NOT add features, error handling, or complexity beyond what's needed to make it compile/run.",
               ""
           ])

       prompt_parts.extend([
           "## Current Code (to be fixed):",
           "```csharp",
           code,
           "```",
           "",
           f"## {context_type.capitalize()} Errors:",
           "```",
           error_logs,
           "```",
           ""
       ])

       # ... existing context sections (API, similar examples, etc.) ...

       prompt_parts.extend([
           "",
           "## Fix Instructions:",
           "1. **Minimal Changes**: Make ONLY the changes needed to fix the errors",
           "2. **Preserve Intent**: The fixed code must demonstrate the SAME concept as the original",
           "3. **No Scope Creep**: Do NOT add error handling, validation, or features not in the original",
           "4. **Teaching Clarity**: A reader should understand the same lesson from your fix",
           "",
           "## Examples of BAD fixes (scope creep):",
           "❌ Adding try-catch blocks when original had none",
           "❌ Adding File.Exists() checks when original assumed file exists",
           "❌ Adding complex error messages when original used simple code",
           "❌ Restructuring code into methods when original was inline",
           "",
           "## Examples of GOOD fixes (minimal):",
           "✅ Adding missing using statement",
           "✅ Fixing typo in variable name",
           "✅ Correcting API method signature",
           "✅ Adding namespace qualification",
           "",
           "Return ONLY the fixed code, nothing else."
       ])

       full_prompt = '\n'.join(prompt_parts)

       # Call LLM
       response = self._call_llm(full_prompt, temperature=0.2)

       return response
   ```

2. **Updated `src/services/compilation_service.py`:**
   ```python
   # In compilation retry loop
   for attempt in range(max_retries):
       # ... existing setup ...

       # Get LLM fix with original code anchor
       llm_response = self.llm_service.fix_code(
           code=current_code,
           error_logs='\n'.join(result.errors),
           context_type="compile",
           api_context=api_context,
           similar_examples=similar_examples,
           scaffolding_hints=payload.scaffolding_hints,
           family_config=family_config,
           section_heading=example.section_heading,
           description_context=example.description_context,
           topic=example.topic,
           original_code=example.original_code  # NEW: Pass original for anchoring
       )
   ```

3. **Updated `src/services/runtime_service.py`:**
   - Similar changes to pass `original_code` to LLM fixes

4. **New test file `tests/test_anchored_prompts.py`:**
   - `test_fix_prompt_includes_original_code_section`
   - `test_fix_prompt_includes_minimal_change_instruction`
   - `test_fix_prompt_includes_intent_preservation_emphasis`
   - `test_fix_prompt_includes_scope_creep_examples`
   - `test_original_code_not_included_if_identical`
   - `test_llm_responses_reference_original`

5. **Forward-compatible migration:**
   - Original code passed to all fix prompts
   - Backward compatible (optional parameter)

### Hard Rules

- ✅ Keep public signatures: Add optional original_code parameter
- ✅ No network in offline tests: Mock LLM responses
- ✅ Deterministic runs: Same prompt → testable
- ✅ No new deps: Use existing LLM service
- ✅ Keep code/docs/tests in sync: Document anchored prompt format

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Original code included correctly; prompts emphasize minimal changes |
| **Completeness** | All fix types anchored; instructions clear; examples provided |
| **Robustness** | Handles missing original; handles identical original/current |
| **Testability** | Tests verify prompt structure; tests verify LLM adherence |
| **Documentation** | Anchored prompt format documented; examples of good/bad fixes |
| **Integration** | Works with compilation and runtime; reduces drift generation |

### Now (Runbook)

```bash
# 1. Update fix_code() method signature
# Add original_code optional parameter

# 2. Update fix_code() prompt building
# Add "Original Code" section when original differs from current

# 3. Add minimal change instructions
# Include examples of scope creep vs minimal fixes

# 4. Update CompilationService to pass original_code
# In retry loop, pass example.original_code

# 5. Update RuntimeService to pass original_code
# In retry loop, pass example.original_code

# 6. Create test file tests/test_anchored_prompts.py
# Test prompt structure and content

# 7. Run tests
pytest tests/test_anchored_prompts.py -v

# 8. Integration test - measure drift reduction
# Run pipeline with/without anchored prompts
# Compare drift scores

# 9. Tune prompt wording based on results
# Adjust emphasis, examples based on LLM behavior

# 10. Document anchored prompt strategy
# Add to docs with examples
```

---

## Taskcard ID-01: Add Drift Score Computation and Tracking

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-01 (No semantic similarity tracking), ID-GAP-06 (No drift observability)

**Priority:** 🟡 **MEDIUM** - Enables ID-02 (drift gate), provides observability

**Role:** Senior engineer delivering drift metrics for intent preservation monitoring.

### Scope

**Fix:**
- Implement semantic similarity scoring between original and fixed code
- Store drift scores in attempts table for all fix attempts
- Add drift metrics to telemetry (avg drift, max drift, drift distribution)
- Create drift analysis CLI command to report on drift patterns
- Support multiple drift metrics (semantic, edit distance, token overlap)

**Allowed paths:**
- `src/core/drift_metrics.py` - new module for drift computation
- `src/core/models.py` - add drift_score to attempt models
- `src/core/database.py` - update attempts table schema
- `src/cli/main.py` - add drift analysis command
- `tests/test_drift_metrics.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli run --family zip`
- Check attempts table has drift_score column populated
- Run `python -m cli analyze-drift --family zip`
- See report:
  ```
  Drift Analysis for family: zip
  ================================
  Total fixes: 45
  Avg drift score: 0.23
  Max drift score: 0.68 (example: zip-example-42)

  Drift distribution:
    0.0-0.2 (minimal): 25 examples (55.6%)
    0.2-0.4 (moderate): 15 examples (33.3%)
    0.4-0.6 (high): 4 examples (8.9%)
    0.6+ (extreme): 1 example (2.2%)

  Top drift examples:
    1. zip-example-42: 0.68 (runtime fix, added error handling)
    2. zip-example-18: 0.55 (compilation fix, restructured code)
  ```

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_drift_metrics.py -v` passes
- Test drift score computation for various code pairs
- Test drift scores stored in database
- Test drift analysis command generates correct report
- Test telemetry includes drift metrics

**Config respected end-to-end:**
- Drift metrics computed for all fixes
- Drift analysis command works on historical data

**No mock data in production paths:**
- Real drift computation on production fixes
- Mock code pairs in tests

### Deliverables

1. **New module `src/core/drift_metrics.py`:**
   ```python
   """
   Drift metrics for intent preservation tracking.

   Provides multiple methods for measuring semantic drift between code versions.
   """
   import re
   import logging
   from typing import Tuple, Dict, Any
   import numpy as np
   from sentence_transformers import SentenceTransformer

   logger = logging.getLogger(__name__)

   # Global embedding model (lazy-loaded)
   _embedding_model = None

   def get_embedding_model() -> SentenceTransformer:
       """Get or initialize embedding model."""
       global _embedding_model
       if _embedding_model is None:
           _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
       return _embedding_model

   def compute_drift_score(
       original: str,
       modified: str,
       metric: str = "semantic_similarity"
   ) -> float:
       """
       Compute drift score between original and modified code.

       Args:
           original: Original code
           modified: Modified code
           metric: Drift metric ("semantic_similarity", "edit_distance", "token_overlap")

       Returns:
           Drift score in [0.0, 1.0] where 0.0 = identical, 1.0 = completely different
       """
       if metric == "semantic_similarity":
           return semantic_similarity_drift(original, modified)
       elif metric == "edit_distance":
           return edit_distance_drift(original, modified)
       elif metric == "token_overlap":
           return token_overlap_drift(original, modified)
       else:
           logger.warning(f"Unknown metric: {metric}, using semantic_similarity")
           return semantic_similarity_drift(original, modified)

   def semantic_similarity_drift(original: str, modified: str) -> float:
       """Compute drift using semantic embeddings."""
       try:
           model = get_embedding_model()

           # Generate embeddings
           orig_emb = model.encode(original, convert_to_numpy=True)
           mod_emb = model.encode(modified, convert_to_numpy=True)

           # Cosine similarity
           similarity = np.dot(orig_emb, mod_emb) / (
               np.linalg.norm(orig_emb) * np.linalg.norm(mod_emb)
           )

           # Convert to drift (inverted)
           drift = 1.0 - float(similarity)
           return max(0.0, min(1.0, drift))
       except Exception as e:
           logger.error(f"Error computing semantic drift: {e}")
           return 0.0  # Assume no drift on error

   def edit_distance_drift(original: str, modified: str) -> float:
       """Compute drift using normalized Levenshtein distance."""
       import difflib

       ratio = difflib.SequenceMatcher(None, original, modified).ratio()
       drift = 1.0 - ratio
       return drift

   def token_overlap_drift(original: str, modified: str) -> float:
       """Compute drift using token overlap (Jaccard distance)."""
       orig_tokens = set(re.findall(r'\w+', original.lower()))
       mod_tokens = set(re.findall(r'\w+', modified.lower()))

       intersection = len(orig_tokens & mod_tokens)
       union = len(orig_tokens | mod_tokens)

       if union == 0:
           return 0.0

       similarity = intersection / union
       drift = 1.0 - similarity
       return drift

   def analyze_drift(original: str, modified: str) -> Dict[str, Any]:
       """
       Comprehensive drift analysis with multiple metrics.

       Returns:
           Dict with drift scores and characteristics
       """
       semantic_drift = semantic_similarity_drift(original, modified)
       edit_drift = edit_distance_drift(original, modified)
       token_drift = token_overlap_drift(original, modified)

       # Compute characteristics
       orig_lines = len(original.strip().split('\n'))
       mod_lines = len(modified.strip().split('\n'))
       line_growth = (mod_lines - orig_lines) / max(orig_lines, 1)

       orig_chars = len(original)
       mod_chars = len(modified)
       char_growth = (mod_chars - orig_chars) / max(orig_chars, 1)

       return {
           'semantic_drift': semantic_drift,
           'edit_drift': edit_drift,
           'token_drift': token_drift,
           'line_growth_ratio': line_growth,
           'char_growth_ratio': char_growth,
           'original_lines': orig_lines,
           'modified_lines': mod_lines,
           'drift_category': categorize_drift(semantic_drift)
       }

   def categorize_drift(drift_score: float) -> str:
       """Categorize drift score into human-readable categories."""
       if drift_score < 0.2:
           return "minimal"
       elif drift_score < 0.4:
           return "moderate"
       elif drift_score < 0.6:
           return "high"
       else:
           return "extreme"
   ```

2. **Updated `src/core/models.py`:**
   ```python
   # Add drift_score to CompileAttempt and RuntimeAttempt
   @dataclass
   class CompileAttempt:
       # ... existing fields ...
       drift_score: Optional[float] = None  # NEW: Drift from original
       drift_metric: Optional[str] = None   # NEW: Metric used

   @dataclass
   class RuntimeAttempt:
       # ... existing fields ...
       drift_score: Optional[float] = None  # NEW
       drift_metric: Optional[str] = None   # NEW
   ```

3. **Updated database schema:**
   ```sql
   ALTER TABLE compile_attempts ADD COLUMN drift_score REAL;
   ALTER TABLE compile_attempts ADD COLUMN drift_metric TEXT;
   ALTER TABLE runtime_attempts ADD COLUMN drift_score REAL;
   ALTER TABLE runtime_attempts ADD COLUMN drift_metric TEXT;
   ```

4. **Updated `src/cli/main.py` - add drift analysis command:**
   ```python
   def analyze_drift(args):
       """Analyze drift patterns in fix attempts."""
       from src.core.database import Database
       from src.core.drift_metrics import categorize_drift

       db = Database(args.db_path)

       # Query all attempts with drift scores
       query = """
           SELECT example_id, drift_score, drift_metric, success
           FROM compile_attempts
           WHERE drift_score IS NOT NULL AND family = ?
           UNION ALL
           SELECT example_id, drift_score, drift_metric, success
           FROM runtime_attempts
           WHERE drift_score IS NOT NULL AND family = ?
       """

       results = db.execute(query, (args.family, args.family)).fetchall()

       if not results:
           print(f"No drift data found for family: {args.family}")
           return

       # Compute statistics
       drift_scores = [r['drift_score'] for r in results if r['drift_score'] is not None]
       avg_drift = sum(drift_scores) / len(drift_scores)
       max_drift = max(drift_scores)

       # Distribution
       minimal = len([s for s in drift_scores if s < 0.2])
       moderate = len([s for s in drift_scores if 0.2 <= s < 0.4])
       high = len([s for s in drift_scores if 0.4 <= s < 0.6])
       extreme = len([s for s in drift_scores if s >= 0.6])

       # Print report
       print(f"Drift Analysis for family: {args.family}")
       print("=" * 50)
       print(f"Total fixes: {len(results)}")
       print(f"Avg drift score: {avg_drift:.2f}")
       print(f"Max drift score: {max_drift:.2f}")
       print()
       print("Drift distribution:")
       print(f"  0.0-0.2 (minimal): {minimal} fixes ({minimal/len(drift_scores)*100:.1f}%)")
       print(f"  0.2-0.4 (moderate): {moderate} fixes ({moderate/len(drift_scores)*100:.1f}%)")
       print(f"  0.4-0.6 (high): {high} fixes ({high/len(drift_scores)*100:.1f}%)")
       print(f"  0.6+ (extreme): {extreme} fixes ({extreme/len(drift_scores)*100:.1f}%)")

       # Top drift examples
       sorted_results = sorted(results, key=lambda r: r['drift_score'], reverse=True)
       print()
       print("Top drift examples:")
       for i, r in enumerate(sorted_results[:10]):
           print(f"  {i+1}. {r['example_id']}: {r['drift_score']:.2f}")

   # Add to CLI parser
   parser_drift = subparsers.add_parser('analyze-drift', help='Analyze drift patterns')
   parser_drift.add_argument('--family', required=True, help='Family to analyze')
   parser_drift.set_defaults(func=analyze_drift)
   ```

5. **New test file `tests/test_drift_metrics.py`:**
   - `test_semantic_similarity_drift_identical_code`
   - `test_semantic_similarity_drift_minimal_change`
   - `test_semantic_similarity_drift_major_change`
   - `test_edit_distance_drift`
   - `test_token_overlap_drift`
   - `test_analyze_drift_comprehensive`
   - `test_categorize_drift`
   - `test_drift_scores_stored_in_database`

6. **Forward-compatible migration:**
   - Drift scores optional (nullable columns)
   - Existing attempts without drift scores continue to work

### Hard Rules

- ✅ Keep public signatures: New module, doesn't affect existing APIs
- ✅ No network in offline tests: Mock embeddings in tests
- ✅ Deterministic runs: Same code → same drift score
- ✅ No new deps: sentence-transformers already used
- ✅ Keep code/docs/tests in sync: Document drift metrics

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Drift scores accurate; multiple metrics work; categorization correct |
| **Completeness** | All metrics implemented; storage works; analysis command comprehensive |
| **Robustness** | Handles edge cases; graceful errors; works with historical data |
| **Testability** | Tests verify all metrics; tests verify storage; tests verify analysis |
| **Documentation** | Drift metrics explained; usage examples; interpretation guide |
| **Integration** | Works with attempts tracking; enables drift gate; provides observability |

### Now (Runbook)

```bash
# 1. Create src/core/drift_metrics.py module
# Implement three drift metrics

# 2. Update models.py to add drift_score fields
# Add to CompileAttempt and RuntimeAttempt

# 3. Add database migrations
# ALTER TABLE statements for drift_score, drift_metric

# 4. Update CompilationService to compute drift
# After each fix, compute drift and store in attempt

# 5. Update RuntimeService to compute drift
# After each fix, compute drift and store in attempt

# 6. Add analyze-drift CLI command
# Implement drift analysis reporting

# 7. Create test file tests/test_drift_metrics.py
# Test all drift metrics

# 8. Run tests
pytest tests/test_drift_metrics.py -v

# 9. Run pipeline to collect drift data
python -m cli run --family zip --max-examples 50

# 10. Analyze drift patterns
python -m cli analyze-drift --family zip

# 11. Tune drift thresholds based on analysis
# Use analysis results to set reasonable max_drift_score
```

---

## Taskcard ID-05: Selective Vector DB Storage

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-05 (Vector DB stores drifted examples causing contagion)

**Priority:** 🟢 **LOW** - Long-term hygiene, prevents future drift

**Role:** Senior engineer delivering drift-aware vector DB for clean example retrieval.

### Scope

**Fix:**
- Only store examples with `drift_score < 0.3` in vector DB
- Create separate "fixed" collection for LLM-fixed examples
- Add drift metadata to vector DB entries
- Filter vector search to exclude high-drift examples
- Provide CLI command to clean polluted vector DB

**Allowed paths:**
- `src/services/vector_db_service.py` - add drift filtering
- `src/pipeline/orchestrator.py` - selective storage based on drift
- `src/cli/main.py` - add vector DB cleanup command
- `tests/test_selective_vector_db.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli run --family zip`
- Verify high-drift examples not stored in vector DB
- Check vector DB metadata includes drift scores
- Run `python -m cli clean-vector-db --family zip --max-drift 0.3`
- Verify high-drift examples removed from vector DB

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_selective_vector_db.py -v` passes
- Test high-drift examples not stored
- Test low-drift examples stored
- Test drift metadata in vector DB
- Test vector search excludes high-drift examples
- Test cleanup command removes high-drift examples

**Config respected end-to-end:**
- Drift threshold for vector DB configurable
- Separate collections for original vs fixed examples

**No mock data in production paths:**
- Real vector DB operations
- Mock vector DB in tests

### Deliverables

1. **Updated `src/services/vector_db_service.py`:**
   ```python
   def add_example(
       self,
       example_id: str,
       code: str,
       metadata: Dict[str, Any],
       drift_score: Optional[float] = None  # NEW
   ) -> bool:
       """
       Add example to vector DB with drift filtering.

       NEW: Only stores examples with drift_score < threshold.
       """
       if not self.is_available():
           return False

       # Check drift threshold
       drift_threshold = metadata.get('drift_threshold', 0.3)

       if drift_score is not None and drift_score >= drift_threshold:
           logger.info(
               f"Skipping vector DB storage for {example_id}: "
               f"drift_score={drift_score:.3f} >= threshold {drift_threshold}"
           )
           return False

       # Add drift metadata
       if drift_score is not None:
           metadata['drift_score'] = drift_score

       # Determine collection (original vs fixed)
       collection_name = "fixed_examples" if metadata.get('source') == 'llm_fixed' else "original_examples"

       # Add to vector DB
       collection = self._get_collection(collection_name)
       collection.add(
           ids=[example_id],
           documents=[code],
           metadatas=[metadata]
       )

       return True

   def search_similar(
       self,
       query_code: str,
       family: str,
       k: int = 3,
       min_similarity: float = 0.7,
       exclude_high_drift: bool = True  # NEW
   ) -> List[Tuple[str, str, float, Dict]]:
       """
       Search for similar examples with drift filtering.

       NEW: Can exclude high-drift examples from results.
       """
       if not self.is_available():
           return []

       # Search both collections
       results = []

       for collection_name in ["original_examples", "fixed_examples"]:
           collection = self._get_collection(collection_name)

           search_results = collection.query(
               query_texts=[query_code],
               n_results=k * 2,  # Get extra to filter
               where={"family": family}
           )

           # Filter by drift if requested
           for i in range(len(search_results['ids'][0])):
               example_id = search_results['ids'][0][i]
               doc = search_results['documents'][0][i]
               distance = search_results['distances'][0][i]
               metadata = search_results['metadatas'][0][i]

               # Exclude high-drift if requested
               if exclude_high_drift and 'drift_score' in metadata:
                   if metadata['drift_score'] >= 0.3:
                       continue

               similarity = 1.0 - distance
               if similarity >= min_similarity:
                   results.append((example_id, doc, similarity, metadata))

       # Sort by similarity and take top k
       results.sort(key=lambda x: x[2], reverse=True)
       return results[:k]

   def clean_high_drift(
       self,
       family: str,
       max_drift: float = 0.3
   ) -> int:
       """
       Remove high-drift examples from vector DB.

       Returns:
           Number of examples removed
       """
       if not self.is_available():
           return 0

       removed_count = 0

       for collection_name in ["original_examples", "fixed_examples"]:
           collection = self._get_collection(collection_name)

           # Query all examples for family
           all_results = collection.get(where={"family": family})

           ids_to_remove = []
           for i, metadata in enumerate(all_results['metadatas']):
               if 'drift_score' in metadata and metadata['drift_score'] >= max_drift:
                   ids_to_remove.append(all_results['ids'][i])

           # Remove high-drift examples
           if ids_to_remove:
               collection.delete(ids=ids_to_remove)
               removed_count += len(ids_to_remove)
               logger.info(f"Removed {len(ids_to_remove)} high-drift examples from {collection_name}")

       return removed_count
   ```

2. **Updated `src/pipeline/orchestrator.py`:**
   ```python
   # In compilation phase, pass drift_score to vector DB
   if self.vector_db_service.is_available():
       try:
           self.vector_db_service.add_example(
               example_id=example.example_id,
               code=fixed_code,
               metadata={
                   'family': family,
                   'source': 'pipeline_compilation_llm_fixed',
                   'verified': False,
                   'compilable': True,
                   'file_path': example.file_path,
                   'fix_attempt': attempt + 1,
               },
               drift_score=drift_score  # NEW: Pass drift score
           )
       except Exception as e:
           logger.debug(f"Failed to add example to vector DB: {e}")
   ```

3. **Updated `src/cli/main.py` - add cleanup command:**
   ```python
   def clean_vector_db(args):
       """Clean high-drift examples from vector DB."""
       from src.services.vector_db_service import VectorDBService
       from src.core.config import ConfigurationManager

       config_manager = ConfigurationManager()
       global_config = config_manager.load_global_config()

       vector_db = VectorDBService(
           persist_directory=global_config.vector_db.persist_directory,
           embedding_model=global_config.vector_db.embedding_model,
           enabled=global_config.vector_db.enabled
       )

       removed = vector_db.clean_high_drift(
           family=args.family,
           max_drift=args.max_drift
       )

       print(f"Removed {removed} high-drift examples from vector DB")

   # Add to CLI parser
   parser_clean = subparsers.add_parser('clean-vector-db', help='Clean high-drift examples from vector DB')
   parser_clean.add_argument('--family', required=True, help='Family to clean')
   parser_clean.add_argument('--max-drift', type=float, default=0.3, help='Maximum drift score to keep')
   parser_clean.set_defaults(func=clean_vector_db)
   ```

4. **New test file `tests/test_selective_vector_db.py`:**
   - `test_high_drift_examples_not_stored`
   - `test_low_drift_examples_stored`
   - `test_drift_metadata_in_vector_db`
   - `test_search_excludes_high_drift`
   - `test_cleanup_removes_high_drift`
   - `test_separate_collections_for_fixed`

5. **Forward-compatible migration:**
   - Existing vector DB continues to work
   - Drift filtering opt-in via parameter

### Hard Rules

- ✅ Keep public signatures: Add optional parameters with defaults
- ✅ No network in offline tests: Mock vector DB
- ✅ Deterministic runs: Same examples → same storage decisions
- ✅ No new deps: Use existing ChromaDB
- ✅ Keep code/docs/tests in sync: Document selective storage strategy

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Drift filtering works; metadata stored correctly; cleanup effective |
| **Completeness** | Selective storage works; search filtering works; cleanup command works; separate collections |
| **Robustness** | Handles missing drift scores; graceful errors; doesn't break existing vector DB |
| **Testability** | Tests verify filtering, storage, search, cleanup |
| **Documentation** | Selective storage strategy documented; drift threshold guidance provided |
| **Integration** | Works with pipeline storage; enables clean retrieval; prevents contagion |

### Now (Runbook)

```bash
# 1. Update VectorDBService.add_example() to check drift threshold
# Add drift_score parameter, filter before storing

# 2. Update VectorDBService.search_similar() to exclude high-drift
# Add exclude_high_drift parameter

# 3. Add VectorDBService.clean_high_drift() method
# Implement cleanup logic

# 4. Update orchestrator to pass drift_score when storing
# In compilation and runtime phases

# 5. Add clean-vector-db CLI command
# Implement cleanup command

# 6. Create test file tests/test_selective_vector_db.py
# Test all selective storage scenarios

# 7. Run tests
pytest tests/test_selective_vector_db.py -v

# 8. Integration test - verify high-drift not stored
# Run pipeline, check vector DB doesn't have high-drift examples

# 9. Run cleanup on existing vector DB
python -m cli clean-vector-db --family zip --max-drift 0.3

# 10. Verify cleanup worked
# Check vector DB size before/after
```

---

## Taskcard ID-06: Drift Metrics Dashboard and Reporting

**Status:** Not Started

**Gap Linkage:** Fixes ID-GAP-06 (No observability into drift metrics)

**Priority:** 🟢 **LOW** - Nice-to-have, improves observability

**Role:** Senior engineer delivering drift observability for continuous monitoring.

### Scope

**Fix:**
- Export drift metrics to telemetry JSON
- Create drift trends report (drift over time, by family)
- Add drift visualization CLI command
- Track drift reduction after improvements
- Alert on drift regression

**Allowed paths:**
- `src/core/telemetry.py` - add drift metrics export
- `src/cli/main.py` - add drift visualization command
- `tests/test_drift_reporting.py` - new test file

**Forbidden:** Any other file/path

### Acceptance Checks

**CLI:**
- Run `python -m cli visualize-drift --family zip`
- See ASCII chart:
  ```
  Drift Distribution (family: zip)
  ================================

  0.0-0.1: ████████████████████ (20)
  0.1-0.2: ████████████ (12)
  0.2-0.3: ██████ (6)
  0.3-0.4: ███ (3)
  0.4-0.5: █ (1)
  0.5-0.6: █ (1)
  0.6-0.7: (0)
  0.7+:    (0)

  Avg drift: 0.18
  Median drift: 0.15
  P95 drift: 0.42
  ```
- Check telemetry JSON includes drift metrics
- Run `python -m cli drift-trends --family zip --last-n-runs 10`
- See trend report

**UI/Web/API:**
- N/A (CLI-only feature)

**Tests:**
- `pytest tests/test_drift_reporting.py -v` passes
- Test drift metrics exported to telemetry
- Test visualization command works
- Test trends analysis works

**Config respected end-to-end:**
- Drift metrics included in telemetry by default
- Visualization and trends commands work on historical data

**No mock data in production paths:**
- Real drift metrics from database
- Mock data in tests

### Deliverables

1. **Updated `src/core/telemetry.py`:**
   - Add drift metrics to telemetry export
   - Include avg_drift, max_drift, drift_distribution

2. **Updated `src/cli/main.py`:**
   - Add `visualize-drift` command with ASCII chart
   - Add `drift-trends` command for temporal analysis

3. **New test file `tests/test_drift_reporting.py`:**
   - Test drift metrics export
   - Test visualization rendering
   - Test trends analysis

### Hard Rules

- ✅ Keep public signatures: New commands, doesn't affect existing
- ✅ No network in offline tests: Mock telemetry
- ✅ Deterministic runs: Same data → same visualization
- ✅ No new deps: Pure Python visualization
- ✅ Keep code/docs/tests in sync: Document drift reporting

### Review Dimensions (5/5 Criteria)

| Dimension | 5/5 Means |
|-----------|-----------|
| **Correctness** | Metrics accurate; visualizations clear; trends correct |
| **Completeness** | All metrics exported; visualization comprehensive; trends insightful |
| **Robustness** | Handles missing data; graceful errors; works with partial data |
| **Testability** | Tests verify metrics, visualization, trends |
| **Documentation** | Drift reporting documented; interpretation guide |
| **Integration** | Works with telemetry; enables monitoring; supports continuous improvement |

---

## Summary

**6 Taskcards Created to Address Intent Drift Problem:**

| Priority | Taskcard | Impact | Effort | Status |
|----------|----------|--------|--------|--------|
| 🔥 HIGH | **ID-04**: Two-Code Final Review | Immediate improvement, catches drift at final gate | 8h | Quick Win |
| 🔥 HIGH | **ID-02**: Drift Threshold Gate | Prevents bad fixes from propagating | 10h | Critical |
| 🟡 MEDIUM | **ID-03**: Original-Anchored Fix Prompts | Reduces drift generation at source | 8h | Preventive |
| 🟡 MEDIUM | **ID-01**: Drift Score Computation | Enables drift gate + observability | 12h | Foundation |
| 🟢 LOW | **ID-05**: Selective Vector DB Storage | Prevents drift contagion long-term | 6h | Hygiene |
| 🟢 LOW | **ID-06**: Drift Metrics Dashboard | Improves observability and monitoring | 6h | Nice-to-have |

**Implementation Order (from `reviews/claude.md`):**
```
[HIGH]   ID-04: Two-Code Final Review  ← Immediate improvement, low risk
[HIGH]   ID-02: Drift Threshold Gate   ← Prevents bad fixes from propagating
[MEDIUM] ID-03: Original-Anchored Prompts ← Reduces drift generation
[MEDIUM] ID-01: Drift Score Computation ← Enables ID-02, provides observability
[LOW]    ID-05: Selective Vector DB    ← Long-term hygiene
[LOW]    ID-06: Drift Metrics Dashboard ← Observability and monitoring
```

**Key Integration Points:**
- **ID-01** provides drift scores for **ID-02** (drift gate)
- **ID-02** uses scores from **ID-01** to reject high-drift fixes
- **ID-03** works alongside **ID-02** to reduce drift generation
- **ID-04** provides final safety net for all fixes
- **ID-05** uses drift scores from **ID-01** for vector DB filtering
- **ID-06** visualizes metrics from **ID-01** for continuous improvement

**Expected Impact:**
- **20-30% reduction** in drift after ID-03 (anchored prompts)
- **40-50% reduction** in high-drift examples reaching production after ID-02 (drift gate)
- **Near-zero** drift examples passing final review after ID-04 (two-code review)
- **Clean vector DB** after ID-05 (no drift contagion)

**Total Estimated Effort:** 50 hours (1.5 weeks for all taskcards)

**Risk Assessment:**
- **Low Risk**: All taskcards (non-breaking, opt-in features, backward compatible)
- **High Value**: Directly addresses critical issue identified in code review
- **Quick Win Available**: ID-04 can be implemented first for immediate improvement
