# Documentation Index

This index summarizes the primary documentation entry points for the repository.

## Architecture

- [Overview](architecture/overview.md): pipeline phases, entities, and data flow.
- [Architecture](architecture/architecture.md): detailed system design, phase controllers, and DB schema.
- [Entry Points](architecture/entrypoints.md): CLI and MCP entry points, command surface, and write guards.
- [MCP Reference](architecture/mcp.md): protocol lifecycle, tool surface, HTTP wrapper, and test guidance.
- [LLM Code Fixing Flow](architecture/llm-code-fixing-flow.md): LLM fix loop internals.
- [Patching Strategies](architecture/patching-strategies.md): deterministic fix patterns.

## Reference

- [Configuration](reference/configuration.md): global and family config settings.
- [API Reference](reference/api-reference.md): HTTP API reference.
- [LLM Model Reference](reference/llm-model-reference.md): supported LLM models and routing.
- [Telemetry](reference/telemetry.md): telemetry recording and exported artifacts.
- [Local Telemetry API](reference/local-telemetry-api.md): telemetry event schema (v3.0.0).

## Operations

- [Operations Runbook](operations/runbook.md): pipeline ops, system ops, and troubleshooting.
- [Performance Benchmarks](operations/performance.md): gist system performance baselines.
- [Failure Analytics Queries](operations/analytics-queries.md): SQL analytics for failure tracking.

## Safety

- [Safety](safety/safety.md): operational safeguards, write guards, and drift controls.

## Development

- [Development Guide](development/development-guide.md): contributing guide, code conventions.
- [Testing Guide](development/testing-guide.md): unit test patterns and fixture conventions.
- [Family KB](development/family-kb.md): knowledge-base subsystem governance.

## Assessment

- [Accuracy Audit](assessments/accuracy-audit.md): family accuracy baselines and audit methodology.
- [Known Gaps](assessments/known-gaps.md): known issues, archive constraints, and missing pieces.

## Internal

- [Backfill](internal/backfill.md): how local caches are populated for test data and references.
- [Announcement](internal/announcement.md): internal team announcement.

## ADRs

- [ADR-0001](adr/0001-verify-fix-verify-pipeline.md): Verify-Fix-Verify pipeline.
- [ADR-0002](adr/0002-deterministic-before-llm.md): Deterministic before LLM.
- [ADR-0003](adr/0003-sqlite-state-machine.md): SQLite state machine.
