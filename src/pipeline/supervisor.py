"""
Run Supervisor — TC-08
Post-run analyzer that reviews pipeline results and emits
structured recommendations: retry candidates, pattern proposals,
and quality alerts. Produces supervisor_report.json.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SUPERVISOR_SCHEMA_VERSION = "1.0"


def analyze_run(
    run_id: str,
    family: str,
    results: Dict[str, Any],
    db: Any,
    artifact_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Analyze pipeline run results and emit supervisor_report.json.

    Args:
        run_id: Pipeline run identifier
        family: Family processed
        results: Pipeline results dict from run_full_pipeline
        db: Database instance
        artifact_dir: Override artifact output directory

    Returns:
        Path to supervisor_report.json, or None on failure
    """
    if artifact_dir is None:
        artifact_dir = Path("artifacts") / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    recommendations = []

    # 1. Identify retry candidates (transient failures)
    retry_candidates = _find_retry_candidates(run_id, family, db)
    if retry_candidates:
        recommendations.append({
            "type": "retry_candidate",
            "example_ids": retry_candidates,
            "reason": "Examples failed with potentially transient errors (timeout, infra)",
            "count": len(retry_candidates),
        })

    # 2. Identify pattern proposals (clustered failure signatures)
    pattern_proposals = _find_pattern_proposals(run_id, family, db)
    for proposal in pattern_proposals:
        recommendations.append({
            "type": "pattern_proposal",
            "signature": proposal["signature"],
            "count": proposal["count"],
            "confidence": proposal["confidence"],
            "reason": f"Error signature appeared {proposal['count']} times",
        })

    # 3. Quality alerts (verification rate concerns)
    quality_alerts = _check_quality(run_id, family, results, db)
    for alert in quality_alerts:
        recommendations.append({
            "type": "quality_alert",
            "metric": alert["metric"],
            "current": alert["current"],
            "threshold": alert["threshold"],
            "reason": alert["reason"],
        })

    report = {
        "schema_version": SUPERVISOR_SCHEMA_VERSION,
        "run_id": run_id,
        "family": family,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "recommendations": recommendations,
        "summary": {
            "retry_candidates": len(retry_candidates),
            "pattern_proposals": len(pattern_proposals),
            "quality_alerts": len(quality_alerts),
            "total_recommendations": len(recommendations),
        },
        "llm_analysis": {
            "enabled": False,
            "summary": None,
        },
    }

    # 4. TC-12: Auto-learn pattern extraction (propose, never auto-promote)
    try:
        from .auto_learn_integration import extract_proposed_patterns
        patterns_path = extract_proposed_patterns(
            run_id=run_id, family=family, db=db, artifact_dir=artifact_dir
        )
        if patterns_path:
            report["auto_learn"] = {
                "enabled": True,
                "patterns_file": str(patterns_path),
            }
        else:
            report["auto_learn"] = {"enabled": True, "patterns_file": None}
    except Exception as al_err:
        logger.debug(f"Auto-learn integration skipped: {al_err}")
        report["auto_learn"] = {"enabled": False, "error": str(al_err)}

    output_path = artifact_dir / "supervisor_report.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Supervisor report written to {output_path}")
        return output_path
    except Exception as e:
        logger.warning(f"Failed to write supervisor report: {e}")
        return None


def _find_retry_candidates(run_id: str, family: str, db: Any) -> List[str]:
    """Find examples that failed with transient/infra errors."""
    try:
        with db.get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT example_id FROM failure_details
                WHERE run_id = ?
                  AND failure_category IN (
                      'timeout', 'infra_missing_test_data',
                      'infra_blocked_format', 'infra_blocked_external'
                  )
                  AND resolution != 'fixed'
            """, (run_id,)).fetchall()
            return [row["example_id"] for row in rows if row["example_id"]]
    except Exception:
        return []


def _find_pattern_proposals(run_id: str, family: str, db: Any) -> List[Dict]:
    """Find clustered failure signatures that could become deterministic fixes."""
    try:
        with db.get_connection() as conn:
            rows = conn.execute("""
                SELECT error_category, COUNT(*) as cnt
                FROM failure_details
                WHERE run_id = ?
                  AND failure_category IN ('compile_error', 'runtime_error')
                  AND error_category IS NOT NULL
                GROUP BY error_category
                HAVING cnt >= 3
                ORDER BY cnt DESC
                LIMIT 5
            """, (run_id,)).fetchall()
            return [
                {
                    "signature": row["error_category"],
                    "count": row["cnt"],
                    "confidence": min(0.9, 0.3 + (row["cnt"] * 0.1)),
                }
                for row in rows
            ]
    except Exception:
        return []


def _check_quality(
    run_id: str, family: str, results: Dict[str, Any], db: Any
) -> List[Dict]:
    """Check for quality concerns in this run."""
    alerts = []
    try:
        stats = db.get_run_stats_from_db(family, run_id)
        total = stats.get("total_processed", 0)
        verified = stats.get("verified", 0)

        if total > 0:
            rate = verified / total
            if rate < 0.5:
                alerts.append({
                    "metric": "verification_rate",
                    "current": round(rate * 100, 1),
                    "threshold": 50.0,
                    "reason": f"Verification rate {rate*100:.1f}% is below 50% threshold",
                })
    except Exception:
        pass

    return alerts
