# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-13

### Added
- Structured JSON logging via `src/core/logging_config.py`
- Security baseline tests (`tests/test_security_baseline.py`)
- Package smoke tests (`tests/test_package_smoke.py`)
- Root-level Dockerfile and docker-compose.yml for containerized deployment
- SECURITY.md with vulnerability reporting policy and security controls
- Architecture Decision Records (ADRs) in `docs/adr/`
- CI security scanning job (bandit + pip-audit)
- CI coverage threshold enforcement (--cov-fail-under=50)
- Local gate script (`scripts/local-gate.sh`)

### Changed
- Bumped version from 0.1.0 to 1.0.0 reflecting production maturity

## [0.9.0] - 2026-04-20

### Added
- Eval baseline infrastructure with accuracy evidence and audit docs
- CODEOWNERS expansion, CONTRIBUTING.md, risky-change checklist
- GitLab CI pipeline with eval validation and coverage reporting
- Circuit breaker, degraded mode, and KB error handling tests

## [0.8.0] - 2026-02-12

### Added
- Dual-database architecture (production/development separation)
- Drift threshold gate with configurable semantic drift detection
- Selective vector DB storage (drift-aware filtering)
- Drift metrics dashboard (ASCII histograms, trend analysis)
- Original-anchored fix prompts for intent preservation
- Two-code final review (Stage 5.5)
- Configurable discovery patterns, content filtering, gist patterns
- Knowledge base (KB) system with behavioral patterns and review hints
- Path guards and provenance guards for write safety
- MCP server interface for Claude Desktop integration

## [0.7.0] - 2026-01-16

### Added
- CI integration with GitHub Actions (static analysis, smoke tests, matrix tests)
- Runtime matrix tests (42 parameterized tests)
- Architecture documentation rewrite
- Repository hygiene (archived analysis scripts)

## [0.1.0] - 2025-12-01

### Added
- Initial verify-fix-verify (VFV) pipeline
- 6-phase pipeline (Discovery, Compilation, Runtime, Markdown Update, Final Review, Finalization)
- Deterministic C# fix patterns (10+ patterns)
- LLM-assisted fixing via OpenAI-compatible API
- SQLite state machine with full audit trail
- CLI interface for all pipeline operations
- 16 product family configurations
