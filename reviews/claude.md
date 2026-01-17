Let me examine the key services involved in this flow to understand where the drift happens.Now let me see the orchestrator to understand how the phases chain together:Let me look at the LLM fix_code method to see how fixes are actually prompted:Now I have a clear picture of the system. Here's my brief diagnostic and plan:

---

## Diagnosis: The Intent Drift Problem

**Root Causes:**

1. **Cumulative Drift** - Each fix phase (compilation × 3 retries + runtime × 3 retries = up to 6 LLM transforms) stacks changes. By the end, code has evolved far from original intent.

2. **No Drift Guard** - The cascading degradation prevention (line 910-922) only checks if build errors *increased*, not if semantic intent was lost.

3. **Fix Prompts Prioritize Execution Over Intent** - Despite "minimal change" instructions, LLMs naturally expand code to make it work (add error handling, file checks, etc).

4. **Final Reviewer Has No Original Context** - Phase E sees only the final mutated code vs markdown, not the delta from original. It asks "does this code match the docs?" but the code has been transformed to run, not to teach.

5. **Polluted Vector DB** - Fixed examples get stored and used as references (lines 499-514, 889-906), causing future fixes to drift toward "working but bloated" patterns.

---

## Brief Fix Plan

### Strategy: **Intent-Anchored Verification**

| Phase | Change | Purpose |
|-------|--------|---------|
| **A. Add Drift Score** | Compute semantic similarity between `original_code` and `current_code` after each fix | Quantify intent loss |
| **B. Drift Threshold Gate** | Reject fixes where `drift_score > 0.4` (configurable) | Stop runaway expansion |
| **C. Original-Anchored Prompts** | Include `original_code` in all fix prompts with explicit instruction: "your fix must remain recognizable as a variant of this original" | Tether LLM to source |
| **D. Two-Code Final Review** | Pass both `original_code` AND `verified_code` to Phase E reviewer. Ask: "Does the verified version preserve the teaching intent of the original while being executable?" | Contextual approval |
| **E. Selective Vector DB** | Only store examples that pass with `drift_score < 0.3` and don't store LLM-fixed examples at all (or store in separate "fixed" collection) | Prevent drift contagion |

### Implementation Priority:

```
[HIGH]   D. Two-Code Final Review  ← Immediate improvement, low risk
[HIGH]   B. Drift Threshold Gate   ← Prevents bad fixes from propagating  
[MEDIUM] C. Original-Anchored Prompts ← Reduces drift generation
[MEDIUM] A. Add Drift Score        ← Enables B, provides observability
[LOW]    E. Selective Vector DB    ← Long-term hygiene
```

---

### Quick Win: Modify Final Review (Phase D)

The fastest path to improvement is modifying `_run_final_review_phase` and `review_markdown_structured` to include the original code alongside the verified code:

```python
# In review prompt, add:
"## Original Example (before any fixes):"
original_code
"## Current Example (after verification):"  
verified_code
"## Evaluation Criteria:"
"1. Does the current code still demonstrate the same concept as the original?"
"2. Would a developer reading the docs get confused by the current code?"
"3. Are the changes necessary for execution, or did they add unrelated features?"
```