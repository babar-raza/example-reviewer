# ADR 0001: Verify-Fix-Verify (VFV) Pipeline Pattern

## Status
Accepted

## Context
Aspose maintains hundreds of C# code examples across markdown documentation.
These examples silently break as APIs evolve — methods renamed, signatures
changed, dependencies updated. Manual validation at scale is impractical.

We needed an automated approach that could:
1. Detect broken examples by actually compiling and running them
2. Fix failures using both deterministic patterns and LLM assistance
3. Verify that fixes are correct before committing back to source

## Decision
We adopted a **Verify-Fix-Verify (VFV)** loop implemented as a 6-phase
pipeline (A through F):

- **Phase A (Discovery):** Scan markdown, extract code blocks and gists
- **Phase B (Compilation):** Wrap in harness, apply deterministic fixes, `dotnet build`, LLM fixes
- **Phase C (Runtime):** Execute binary, resolve fixtures, LLM fixes for runtime errors
- **Phase D (Markdown Update):** Overwrite verified code blocks in source markdown
- **Phase E (Final Review):** LLM semantic drift validation
- **Phase F (Finalization):** Git commit, telemetry export

Each phase gates on the previous phase's success. The pipeline tracks state
per-example in SQLite, enabling resume and partial re-runs.

## Consequences
- **Positive:** End-to-end automation from broken example to committed fix
- **Positive:** Deterministic fixes applied first (no LLM cost for common patterns)
- **Positive:** State machine enables partial runs, debugging, and audit
- **Negative:** Pipeline complexity requires careful orchestrator design
- **Negative:** Requires .NET SDK in runtime environment
