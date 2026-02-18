# src/pipeline/ - Pipeline Orchestration

Controls the VFV (Verify-Fix-Verify) pipeline flow.

## Files

| File | Purpose |
|------|---------|
| `orchestrator.py` | Main pipeline orchestrator - drives all phases (discover, compile, fix, verify, review, commit) |
| `error_router.py` | Routes compiler/runtime errors to appropriate fix strategies |
| `error_complexity_classifier.py` | Classifies error complexity (trivial, moderate, complex) |
| `risk_classifier.py` | Assesses risk level of code changes |
| `escalation_classifier.py` | Determines when to escalate to LLM vs deterministic fix |
| `app_context_classifier.py` | Classifies code as console app, library, or ASP.NET |
| `family_service_registry.py` | Per-family service configuration registry |
| `failure_tracker.py` | Tracks failure patterns across pipeline runs |
| `context_drift_validator.py` | Validates code changes haven't drifted from original intent |
