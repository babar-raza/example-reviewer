"""
Auto-Learn Integration — TC-12
Post-run pattern extraction integrated into the supervisor flow.
Analyzes failures from a completed run, clusters by error signature,
and proposes patterns to artifacts/<run_id>/proposed_patterns.json.

Patterns are PROPOSED only — never auto-promoted to active fixes.
Human review is required before any pattern becomes operational.
"""

import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_proposed_patterns(
    run_id: str,
    family: str,
    db: Any,
    artifact_dir: Optional[Path] = None,
) -> Optional[Path]:
    """
    Extract failure patterns from a completed run and write proposals.

    Args:
        run_id: Pipeline run identifier
        family: Family that was processed
        db: Database instance with get_connection()
        artifact_dir: Override artifact directory

    Returns:
        Path to proposed_patterns.json, or None if no patterns found
    """
    if artifact_dir is None:
        artifact_dir = Path("artifacts") / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Fetch failed examples from this run
    failures = _get_failed_examples(run_id, db)
    if not failures:
        logger.debug(f"No failures found for run {run_id}, skipping auto-learn")
        return None

    # Cluster by error signature
    clusters = _cluster_by_signature(failures)
    if not clusters:
        return None

    # Extract pattern proposals (never auto-approved)
    proposals = []
    for signature, examples in clusters.items():
        proposal = _build_proposal(signature, examples, family)
        if proposal:
            proposals.append(proposal)

    if not proposals:
        return None

    manifest = {
        "schema_version": "1.0",
        "run_id": run_id,
        "family": family,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total_failures_analyzed": len(failures),
        "clusters_found": len(clusters),
        "proposals": proposals,
        "auto_promoted": False,
        "requires_human_review": True,
    }

    output_path = artifact_dir / "proposed_patterns.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(
            f"Auto-learn: {len(proposals)} pattern proposals written to {output_path}"
        )
        return output_path
    except Exception as e:
        logger.warning(f"Failed to write proposed patterns: {e}")
        return None


def _get_failed_examples(run_id: str, db: Any) -> List[Dict]:
    """Fetch failed examples from the run via Database connection."""
    try:
        with db.get_connection() as conn:
            rows = conn.execute("""
                SELECT ers.example_id, ers.status, ers.failure_reason,
                       ers.escalation_reason
                FROM example_run_state ers
                WHERE ers.run_id = ?
                  AND ers.status IN (
                      'COMPILE_FAILED', 'RUNTIME_FAILED', 'INFRA_BLOCKED'
                  )
            """, (run_id,)).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.debug(f"Could not fetch failures for auto-learn: {e}")
        return []


def _cluster_by_signature(failures: List[Dict]) -> Dict[str, List[Dict]]:
    """Group failures by extracted error signature."""
    clusters: Dict[str, List[Dict]] = defaultdict(list)
    for f in failures:
        reason = (
            f.get("failure_reason")
            or f.get("escalation_reason")
            or "unknown"
        )
        cs_match = re.search(r"CS\d{4}", reason)
        if cs_match:
            sig = cs_match.group(0)
        elif "timeout" in reason.lower():
            sig = "TIMEOUT"
        elif "password" in reason.lower():
            sig = "PASSWORD_ISSUE"
        elif "missing" in reason.lower() and "file" in reason.lower():
            sig = "MISSING_FILE"
        else:
            sig = f"OTHER_{f.get('status', 'UNKNOWN')}"
        clusters[sig].append(f)
    return dict(clusters)


def _build_proposal(
    signature: str, examples: List[Dict], family: str
) -> Optional[Dict]:
    """Build a single pattern proposal from a cluster."""
    count = len(examples)

    # Determine pattern type and confidence
    if signature.startswith("CS"):
        pattern_type = "compile_error"
        known_codes = {"CS0246", "CS0103", "CS7036", "CS0104", "CS0029", "CS1061"}
        confidence = 0.7 if signature in known_codes else 0.4
        suggestion = f"Investigate {signature} fix pattern across {count} examples"
    elif signature == "TIMEOUT":
        pattern_type = "transient"
        confidence = 0.3
        suggestion = f"Consider retry or timeout increase for {count} examples"
    elif signature == "PASSWORD_ISSUE":
        pattern_type = "infra_blocked"
        confidence = 0.3
        suggestion = "Regenerate password fixtures"
    elif signature == "MISSING_FILE":
        pattern_type = "infra_blocked"
        confidence = 0.3
        suggestion = "Add missing test data files"
    else:
        pattern_type = "unknown"
        confidence = 0.2
        suggestion = f"Manual investigation needed for {count} examples"

    return {
        "signature": signature,
        "pattern_type": pattern_type,
        "example_count": count,
        "confidence": round(confidence, 2),
        "suggestion": suggestion,
        "example_ids": [e["example_id"] for e in examples[:10]],
        "auto_approved": False,
        "family": family,
    }
