# ADR 0002: Deterministic Fixes Before LLM

## Status
Accepted

## Context
Many compilation failures in C# examples follow predictable patterns:
missing `using` directives, stream disposal issues, enum name changes,
constructor signature updates. Calling an LLM for these adds unnecessary
cost (tokens) and latency, and introduces non-determinism.

## Decision
The pipeline applies **10+ deterministic fix patterns** before invoking
the LLM. These patterns are implemented in `src/services/semantic_microfixes.py`
and family-specific fix modules (e.g., `src/services/family_fixes/zip_fixes.py`).

Deterministic patterns include:
- Adding missing `using` directives based on error messages
- Stream disposal wrapping (`using` statements)
- Enum member name corrections (via API catalog lookup)
- Constructor signature adjustments
- Namespace corrections

The LLM is called only when deterministic patterns cannot resolve the error.

## Consequences
- **Positive:** Reduces LLM API costs significantly (most errors are pattern-fixable)
- **Positive:** Deterministic fixes are reproducible and testable
- **Positive:** Faster turnaround for common error types
- **Negative:** Requires maintaining pattern library as APIs evolve
- **Negative:** New error patterns need manual addition to the deterministic layer
