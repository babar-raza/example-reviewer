"""
Run Evidence Manifest — TC-01
Emits a machine-readable run_evidence.json after each pipeline run,
consumable by the reviewer application's vCollect step.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

EVIDENCE_SCHEMA_VERSION = "1.0"


def emit_run_evidence(
    run_id: str,
    family: str,
    results: Dict[str, Any],
    db: Any,
    artifact_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Write run_evidence.json to the artifacts directory for this run.

    Args:
        run_id: Pipeline run identifier
        family: Family being processed
        results: Pipeline results dictionary from run_full_pipeline
        db: Database instance for querying run stats
        artifact_dir: Override artifact output directory

    Returns:
        Path to the written evidence file, or None on failure
    """
    if artifact_dir is None:
        artifact_dir = Path("artifacts") / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    try:
        db_stats = db.get_run_stats_from_db(family, run_id)
    except Exception:
        db_stats = {"total_processed": 0, "verified": 0, "failed": 0}

    discovery = results.get("phases", {}).get("discovery", {})
    total = db_stats.get("total_processed", 0)
    verified = db_stats.get("verified", 0)
    failed = db_stats.get("failed", 0)
    skipped = max(0, total - verified - failed)
    verification_rate = round((verified / total) * 100, 1) if total > 0 else 0.0

    # Collect phase timing from results
    phases = {}
    for phase_name in ["discovery", "compilation", "runtime", "markdown_update", "final_review", "finalization"]:
        phase_data = results.get("phases", {}).get(phase_name, {})
        phases[phase_name] = {
            "status": "completed" if phase_data else "skipped",
            "examples_processed": phase_data.get("examples_found", phase_data.get("examples_processed", 0)),
        }

    # LLM usage summary
    llm_metrics = results.get("llm_metrics", {})
    circuit_breaker_state = results.get("circuit_breaker_state", "unknown")

    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "run_id": run_id,
        "family": family,
        "started_at": results.get("started_at", ""),
        "completed_at": results.get("completed_at", ""),
        "success": results.get("success", False),
        "examples": {
            "discovered": discovery.get("examples_found", 0),
            "verified": verified,
            "failed": failed,
            "skipped": skipped,
        },
        "phases": phases,
        "llm": {
            "calls": llm_metrics.get("total_calls", 0),
            "tokens": llm_metrics.get("total_tokens", 0),
            "fallback_count": llm_metrics.get("fallback_count", 0),
            "circuit_breaker_state": circuit_breaker_state,
        },
        "verification_rate_pct": verification_rate,
        "terminal_statuses": {
            "VERIFIED": verified,
            "FAILED": failed,
            "SKIPPED": skipped,
        },
        "error": results.get("error"),
    }

    output_path = artifact_dir / "run_evidence.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)
        logger.info(f"Run evidence manifest written to {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"Failed to write run evidence manifest: {e}")
        return None
