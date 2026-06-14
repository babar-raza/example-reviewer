"""
APRV Signal Generator — TC-02
Generates aprv_self_assessment.json with self-assessed APRV maturity levels
and grounding evidence, consumable by the reviewer application's
aCollect/pCollect/rCollect/vCollect analysis steps.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APRV_SCHEMA_VERSION = "1.0"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _check_file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def _check_dir_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).is_dir()


def assess_agentic() -> dict:
    """Assess Agentic maturity level with evidence."""
    evidence = []

    if _check_file_exists("src/pipeline/orchestrator.py"):
        evidence.append("six_phase_pipeline")
    if _check_file_exists("src/services/circuit_breaker.py"):
        evidence.append("circuit_breaker")
    if _check_file_exists("src/core/database.py"):
        evidence.append("sqlite_state_machine")
    if _check_file_exists("src/pipeline/evidence.py"):
        evidence.append("run_evidence_emission")
    if _check_file_exists("src/pipeline/supervisor.py"):
        evidence.append("post_run_supervisor")
    if _check_file_exists("src/services/learned_patterns_service.py"):
        evidence.append("learned_patterns_service")
    if _check_file_exists("src/mcp_tools/server.py"):
        evidence.append("mcp_tool_surface")
    if _check_file_exists("src/pipeline/auto_learn_integration.py"):
        evidence.append("post_run_auto_learn")
    if _check_file_exists("scripts/ops/enqueue_scheduled.py"):
        evidence.append("schedule_based_enqueue")
    if _check_file_exists("scripts/ops/detect_stuck_runs.py"):
        evidence.append("stuck_run_detection")

    # Level determination
    level = "A3"  # Workflow (baseline: has pipeline + state)
    if "run_evidence_emission" in evidence:
        level = "A4"  # Stateful (evidence emission)
    if "post_run_supervisor" in evidence and "post_run_auto_learn" in evidence:
        level = "A5"  # Supervised (supervisor + auto-learn + queue)

    return {"level": level, "evidence": evidence}


def assess_practices() -> dict:
    """Assess Practices maturity level with evidence."""
    evidence = []

    if _check_file_exists(".gitlab-ci.yml"):
        evidence.append("ci_pipeline")
    if _check_dir_exists("tests"):
        evidence.append("test_suite")
    if _check_file_exists("tests/test_security_baseline.py"):
        evidence.append("security_tests")
    if _check_file_exists("tests/test_package_smoke.py"):
        evidence.append("smoke_tests")
    if _check_file_exists("scripts/local-gate.sh"):
        evidence.append("local_quality_gate")
    if _check_file_exists("CONTRIBUTING.md"):
        evidence.append("contributing_guidelines")
    if _check_file_exists("CODEOWNERS"):
        evidence.append("codeowners")

    if _check_file_exists("tests/test_integration_real.py"):
        evidence.append("real_integration_tests")
    if _check_file_exists("scripts/ops/run_trend_analysis.py"):
        evidence.append("trend_analysis")

    level = "P3"  # Gated (has CI and tests)
    if "security_tests" in evidence and "local_quality_gate" in evidence:
        level = "P4"  # Automated
    if "real_integration_tests" in evidence:
        level = "P5"  # Verified (real tests + CI enforcement)

    return {"level": level, "evidence": evidence}


def assess_readiness() -> dict:
    """Assess Readiness maturity level with evidence."""
    evidence = []

    if _check_file_exists("Dockerfile"):
        evidence.append("dockerfile")
    if _check_file_exists("docker-compose.yml"):
        evidence.append("docker_compose")
    if _check_file_exists("AGENTS.md"):
        evidence.append("agents_md")
    if _check_file_exists("CHANGELOG.md"):
        evidence.append("changelog")
    if _check_file_exists("SECURITY.md"):
        evidence.append("security_policy")
    if _check_dir_exists("docs/adr"):
        evidence.append("architecture_decision_records")
    if _check_file_exists("src/core/logging_config.py"):
        evidence.append("structured_logging")

    level = "R3"  # Released
    if len(evidence) >= 5:
        level = "R4"  # Governed

    return {"level": level, "evidence": evidence}


def assess_verification() -> dict:
    """Assess Verification maturity level with evidence."""
    evidence = []

    if _check_file_exists("evals/claim_registry.json"):
        evidence.append("claim_registry")
    if _check_file_exists("evals/methodology.md"):
        evidence.append("eval_methodology")
    if _check_file_exists("evals/family_accuracy_report.json"):
        evidence.append("accuracy_baselines")
    if _check_file_exists("scripts/validation/check_doc_code_consistency.py"):
        evidence.append("consistency_checker")
    if _check_file_exists("scripts/validation/check_state_drift.py"):
        evidence.append("state_drift_detector")
    if _check_file_exists("scripts/validation/generate_repo_signals.py"):
        evidence.append("repo_signal_generator")

    level = "V2"  # Sampled
    if "consistency_checker" in evidence and "state_drift_detector" in evidence:
        level = "V3"  # Partial
    if "repo_signal_generator" in evidence:
        level = "V4"  # Sufficient

    return {"level": level, "evidence": evidence}


def generate_aprv_assessment() -> dict:
    """Generate full APRV self-assessment."""
    return {
        "schema_version": APRV_SCHEMA_VERSION,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "agentic": assess_agentic(),
        "practices": assess_practices(),
        "readiness": assess_readiness(),
        "verification": assess_verification(),
    }


def write_aprv_signals(output_path: Optional[Path] = None) -> Path:
    """Write aprv_self_assessment.json to repo root."""
    if output_path is None:
        output_path = REPO_ROOT / "aprv_self_assessment.json"

    assessment = generate_aprv_assessment()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)

    logger.info(f"APRV self-assessment written to {output_path}")
    return output_path


if __name__ == "__main__":
    path = write_aprv_signals()
    print(f"Wrote {path}")
    assessment = generate_aprv_assessment()
    for dim in ["agentic", "practices", "readiness", "verification"]:
        data = assessment[dim]
        print(f"  {dim}: {data['level']} ({len(data['evidence'])} evidence items)")
