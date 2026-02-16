# Opus vs E2E Branch: Example Comparison

**Date**: 2026-02-04 15:48
**Status**: PARTIAL (opus run in progress)

## Target Examples

### 3cfbe24103597fb6 (Simple - 86 chars)
- Code: `using (Archive archiveFile = new Archive()) { }`
- Requires: Just a using block around Archive constructor

### 030d7853ca1ccfdc (Hard - complex code)
- Code: Has undefined variable, method hallucinations
- Difficulty: Semantic understanding required

## Results

### fix/e2e-verify-maturation Branch

| Example ID          | Status     | Details |
|---------------------|------------|---------|
| 3cfbe24103597fb6    | ✓ PASSED   | `compiled_first_try: 1, verified: 1` |
| 030d7853ca1ccfdc    | ✗ FAILED   | Failed across 7 code models |

### opus-example-reviewer-pipeline Branch

| Example ID          | Status | Details |
|---------------------|--------|---------|
| 3cfbe24103597fb6    | PENDING | Full run in progress (390 examples) |
| 030d7853ca1ccfdc    | PENDING | Full run in progress (390 examples) |

**Initial Opus Run Results**:
- Discovered: 390 examples (including both targets)
- Processed: 2 examples only
  - Example c3befb8a (79cc3a8e695caa3c): ✓ Compiled successfully
  - Example 6e1dcba7 (8163c1835c9135fb): ✗ Failed (empty_code)
- Configuration: qwen2.5:14b, temp 0.2, non-deterministic

## Key Difference

**Cannot directly compare yet** because:
1. opus run only processed 2 examples so far (not including our targets)
2. Full run currently executing
3. opus uses different model parameters (temp 0.2, non-deterministic) vs e2e (temp 0.0, deterministic)

## Expected Outcome

Based on architectural differences:
- **Simple example (3cfbe24103597fb6)**: Likely to PASS on opus (if it's as trivial as on e2e)
- **Hard example (030d7853ca1ccfdc)**: Likely to FAIL on opus (same LLM limitations)

Will update when opus run completes.
