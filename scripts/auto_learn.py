#!/usr/bin/env python3
"""
Auto-Learn — Extract patterns from pipeline runs and propose new fixes.

Analyzes failed examples from a pipeline run, clusters them by error signature,
extracts generalizable patterns, and stores them in the learned_patterns table.

High-confidence patterns (types in API catalog) are auto-approved.
Complex transforms require human review.

Usage:
    python scripts/auto_learn.py --family zip
    python scripts/auto_learn.py --family zip --run-id <run_id>
    python scripts/auto_learn.py --family zip --dry-run
    python scripts/auto_learn.py --family zip --use-llm  # LLM-powered extraction

HEAL-10: Phase C Auto-Learn Script
Auto-Learn LLM Integration: 2026-02-06
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
MAIN_DB = PROJECT_ROOT / "data" / "example_reviewer.db"
CATALOG_DB = PROJECT_ROOT / "data" / "api_catalog.db"


def get_latest_run_id(family: str) -> Optional[str]:
    """Get the most recent run ID for a family."""
    conn = sqlite3.connect(str(MAIN_DB))
    c = conn.cursor()
    c.execute(
        "SELECT run_id FROM run_records WHERE family = ? ORDER BY started_at DESC LIMIT 1",
        (family,),
    )
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_failed_examples(run_id: str) -> List[Dict]:
    """Get all failed examples from a run with their error details."""
    conn = sqlite3.connect(str(MAIN_DB))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """SELECT ers.example_id, ers.status, ers.failure_reason, ers.escalation_reason,
                  ers.compilable_code, er.original_code, er.source_type
           FROM example_run_state ers
           JOIN example_records er ON ers.example_id = er.example_id
           WHERE ers.run_id = ?
             AND ers.status IN ('COMPILE_FAILED', 'RUNTIME_FAILED', 'INFRA_BLOCKED')""",
        (run_id,),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def cluster_by_error_signature(failures: List[Dict]) -> Dict[str, List[Dict]]:
    """Group failures by error signature (error code + pattern)."""
    clusters = defaultdict(list)
    for f in failures:
        reason = f.get("failure_reason") or f.get("escalation_reason") or "unknown"
        # Extract CS error code if present
        cs_match = re.search(r"CS\d{4}", reason)
        if cs_match:
            signature = cs_match.group(0)
        elif "password" in reason.lower():
            signature = "PASSWORD_ISSUE"
        elif "missing" in reason.lower() and "file" in reason.lower():
            signature = "MISSING_FILE"
        else:
            signature = f"OTHER_{f['status']}"
        clusters[signature].append(f)
    return dict(clusters)


def extract_patterns(clusters: Dict[str, List[Dict]], family: str) -> List[Dict]:
    """Extract learnable patterns from failure clusters."""
    patterns = []

    for signature, examples in clusters.items():
        pattern = {
            "family": family,
            "error_signature": signature,
            "example_count": len(examples),
            "pattern_type": "unknown",
            "fix_template": "",
            "confidence": 0.0,
            "auto_approved": False,
            "source": "auto_learn",
        }

        if signature.startswith("CS"):
            pattern["pattern_type"] = "compile_error"
            # High confidence if it's a known error code
            if signature in ("CS0246", "CS0103", "CS7036", "CS0104"):
                pattern["confidence"] = 0.8
                pattern["fix_template"] = f"Apply semantic microfix for {signature}"
            else:
                pattern["confidence"] = 0.5
                pattern["fix_template"] = f"Investigate {signature} for {len(examples)} examples"

        elif signature == "PASSWORD_ISSUE":
            pattern["pattern_type"] = "infra_blocked"
            pattern["confidence"] = 0.3
            pattern["fix_template"] = "Regenerate password fixtures with correct password"

        elif signature == "MISSING_FILE":
            pattern["pattern_type"] = "infra_blocked"
            pattern["confidence"] = 0.3
            pattern["fix_template"] = "Add missing test data fixture"

        else:
            pattern["pattern_type"] = "unknown"
            pattern["confidence"] = 0.2

        # Auto-approve high confidence patterns
        if pattern["confidence"] >= 0.8:
            pattern["auto_approved"] = True

        patterns.append(pattern)

    return patterns


class LLMPatternExtractor:
    """
    LLM-powered pattern extraction from failure clusters.

    Uses an LLM to analyze groups of failed examples and generate executable fix patterns
    instead of simple text descriptions.
    """

    EXTRACTION_PROMPT = """Analyze these {count} failed C# code examples with error signature: {signature}

## Failed Examples:
{examples}

## Task:
Generate a reusable, executable fix pattern that could automatically fix similar errors.

## IMPORTANT: Return ONLY valid JSON (no markdown, no explanation):
{{
    "fix_type": "regex_replace|using_directive|code_transform|llm_prompt",
    "fix_code": {{
        "pattern": "regex pattern if fix_type is regex_replace",
        "replacement": "replacement string with $1, $2 for groups",
        "directive": "using Namespace; if fix_type is using_directive",
        "trigger_type": "TypeName that should trigger this directive",
        "transformer": "function_name if fix_type is code_transform",
        "prompt": "prompt template if fix_type is llm_prompt"
    }},
    "confidence": 0.5,
    "fix_template": "Human-readable description of what this fix does",
    "example_before": "Short code snippet showing the error pattern",
    "example_after": "Short code snippet showing the fixed version"
}}

## Guidelines:
- For CS0246 (missing type), use fix_type="using_directive" with the correct namespace
- For simple text replacements, use fix_type="regex_replace"
- For complex multi-step fixes, use fix_type="llm_prompt"
- Confidence should reflect how generalizable the fix is (0.3-0.9)
- Keep examples short (3-5 lines max)
"""

    def __init__(self, llm_service: Any):
        """
        Initialize with an LLM service instance.

        Args:
            llm_service: Instance of LLMService from src.services.llm_service
        """
        self.llm_service = llm_service

    def extract_patterns_with_llm(
        self,
        cluster: Dict[str, Any],
        family: str,
    ) -> List[Dict]:
        """
        Use LLM to analyze a failure cluster and extract executable patterns.

        Args:
            cluster: Dict with 'signature' and 'examples' keys
            family: Product family (e.g., 'zip')

        Returns:
            List of pattern dicts ready for storage (with fix_code populated)
        """
        signature = cluster["signature"]
        examples = cluster["examples"][:5]  # Limit to 5 examples for prompt

        # Format examples for the prompt
        examples_text = self._format_examples(examples)

        prompt = self.EXTRACTION_PROMPT.format(
            count=len(examples),
            signature=signature,
            examples=examples_text,
        )

        try:
            # Use the LLM to extract patterns
            response = self.llm_service.complete(
                prompt=prompt,
                system_prompt="You are a code pattern analysis expert. Return ONLY valid JSON.",
                temperature=0.2,
            )

            if not response.success:
                logger.warning(f"LLM extraction failed for {signature}: {response.error}")
                return []

            # Parse the JSON response
            pattern_data = self._parse_llm_response(response.content, signature, family)
            if pattern_data:
                return [pattern_data]

        except Exception as e:
            logger.error(f"Error during LLM extraction for {signature}: {e}")

        return []

    def _format_examples(self, examples: List[Dict]) -> str:
        """Format examples for the LLM prompt."""
        formatted = []
        for i, ex in enumerate(examples, 1):
            code = ex.get("compilable_code") or ex.get("original_code") or "N/A"
            error = ex.get("failure_reason") or ex.get("escalation_reason") or "Unknown error"
            # Truncate long code
            if len(code) > 500:
                code = code[:500] + "\n// ... (truncated)"
            formatted.append(f"### Example {i}\n**Error**: {error}\n**Code**:\n```csharp\n{code}\n```")
        return "\n\n".join(formatted)

    def _parse_llm_response(
        self,
        content: str,
        signature: str,
        family: str,
    ) -> Optional[Dict]:
        """Parse and validate the LLM response."""
        # Try to extract JSON from the response
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response content: {content[:200]}")
            return None

        # Validate required fields
        fix_type = data.get("fix_type", "template")
        if fix_type not in ("regex_replace", "using_directive", "code_transform", "llm_prompt", "template"):
            logger.warning(f"Invalid fix_type: {fix_type}")
            fix_type = "template"

        fix_code = data.get("fix_code", {})
        confidence = float(data.get("confidence", 0.5))

        # Validate fix_code based on fix_type
        if fix_type == "regex_replace" and not fix_code.get("pattern"):
            logger.warning("regex_replace requires 'pattern' in fix_code")
            fix_type = "template"
            fix_code = {}

        if fix_type == "using_directive" and not fix_code.get("directive"):
            logger.warning("using_directive requires 'directive' in fix_code")
            fix_type = "template"
            fix_code = {}

        # Determine pattern_type from signature
        if signature.startswith("CS"):
            pattern_type = "compile_error"
        elif signature in ("PASSWORD_ISSUE", "MISSING_FILE", "MISSING_DIRECTORY"):
            pattern_type = "infra_blocked"
        else:
            pattern_type = "runtime_error"

        return {
            "family": family,
            "error_signature": signature,
            "pattern_type": pattern_type,
            "fix_type": fix_type,
            "fix_code": fix_code if fix_code else None,
            "fix_template": data.get("fix_template", f"LLM-generated fix for {signature}"),
            "confidence": min(0.9, max(0.1, confidence)),  # Clamp to 0.1-0.9
            "auto_approved": confidence >= 0.8,
            "priority": 50,
            "requires_llm": fix_type == "llm_prompt",
            "example_before": data.get("example_before"),
            "example_after": data.get("example_after"),
            "source": "auto_learn_llm",
        }


def extract_patterns_with_llm(
    clusters: Dict[str, List[Dict]],
    family: str,
    llm_service: Any,
) -> List[Dict]:
    """
    Extract patterns from all clusters using LLM.

    Args:
        clusters: Dict mapping signature -> list of failed examples
        family: Product family
        llm_service: LLM service instance

    Returns:
        List of patterns with executable fix_code
    """
    extractor = LLMPatternExtractor(llm_service)
    patterns = []

    for signature, examples in clusters.items():
        logger.info(f"Extracting pattern for {signature} ({len(examples)} examples)...")
        cluster_patterns = extractor.extract_patterns_with_llm(
            {"signature": signature, "examples": examples},
            family,
        )
        patterns.extend(cluster_patterns)

    return patterns


def store_patterns(patterns: List[Dict], run_id: str, dry_run: bool = False) -> int:
    """Store patterns in the catalog database (supports V2 schema with fix_code)."""
    if dry_run:
        for p in patterns:
            fix_type = p.get("fix_type", "template")
            has_fix_code = bool(p.get("fix_code"))
            logger.info(
                f"  [DRY RUN] {p['error_signature']}: "
                f"type={p['pattern_type']}, "
                f"fix_type={fix_type}, "
                f"has_fix_code={has_fix_code}, "
                f"conf={p['confidence']:.1f}, "
                f"auto={p['auto_approved']}"
            )
        return 0

    conn = sqlite3.connect(str(CATALOG_DB))
    inserted = 0

    for p in patterns:
        try:
            # Serialize fix_code to JSON if present
            fix_code_json = None
            if p.get("fix_code"):
                fix_code_json = json.dumps(p["fix_code"])

            conn.execute(
                """INSERT INTO learned_patterns
                   (family, pattern_type, error_signature, fix_template,
                    fix_type, fix_code, confidence, auto_approved, priority,
                    requires_llm, example_before, example_after, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p["family"],
                    p["pattern_type"],
                    p["error_signature"],
                    p["fix_template"],
                    p.get("fix_type", "template"),
                    fix_code_json,
                    p["confidence"],
                    p["auto_approved"],
                    p.get("priority", 50),
                    p.get("requires_llm", False),
                    p.get("example_before"),
                    p.get("example_after"),
                    p.get("source", "auto_learn"),
                ),
            )
            pattern_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Initialize performance tracking
            conn.execute(
                "INSERT INTO pattern_performance (pattern_id, family) VALUES (?, ?)",
                (pattern_id, p["family"]),
            )

            # Record learning history
            conn.execute(
                """INSERT INTO learning_history
                   (family, run_id, pattern_type, fix_applied,
                    auto_approved, confidence, validation_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    p["family"],
                    run_id,
                    p["pattern_type"],
                    p["fix_template"],
                    p["auto_approved"],
                    p["confidence"],
                    "validated" if p["auto_approved"] else "pending",
                ),
            )
            inserted += 1
            logger.info(f"Stored pattern {pattern_id}: {p['error_signature']} ({p.get('fix_type', 'template')})")
        except sqlite3.IntegrityError as e:
            logger.debug(f"Pattern already exists: {e}")

    conn.commit()
    conn.close()
    return inserted


def update_performance(family: str) -> None:
    """Update success rates for tracked patterns."""
    conn = sqlite3.connect(str(CATALOG_DB))
    conn.execute(
        """UPDATE pattern_performance
           SET success_rate = CASE
               WHEN times_applied > 0 THEN CAST(times_succeeded AS REAL) / times_applied
               ELSE 0.0
           END
           WHERE family = ?""",
        (family,),
    )

    # Report low-performing patterns
    low_perf = conn.execute(
        """SELECT pp.pattern_id, lp.error_signature, pp.success_rate, pp.times_applied
           FROM pattern_performance pp
           JOIN learned_patterns lp ON pp.pattern_id = lp.id
           WHERE pp.family = ?
             AND pp.times_applied >= 10
             AND pp.success_rate < pp.retire_if_below_threshold""",
        (family,),
    ).fetchall()

    for row in low_perf:
        logger.warning(
            f"Low-performing pattern {row[0]} ({row[1]}): "
            f"success_rate={row[2]:.1%} after {row[3]} uses"
        )

    conn.commit()
    conn.close()


def _get_llm_service():
    """Initialize LLM service if available."""
    try:
        # Add project root to path for imports
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.services.llm_service import LLMService

        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, LLM extraction unavailable")
            return None

        service = LLMService()
        if service.is_available():
            return service
        logger.warning("LLM service not available")
        return None
    except ImportError as e:
        logger.warning(f"Could not import LLM service: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error initializing LLM service: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Auto-learn fix patterns from pipeline runs")
    parser.add_argument("--family", required=True, help="Product family")
    parser.add_argument("--run-id", help="Specific run ID (default: latest)")
    parser.add_argument("--dry-run", action="store_true", help="Print patterns without storing")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for intelligent pattern extraction")
    args = parser.parse_args()

    if not MAIN_DB.exists():
        logger.error(f"Main database not found: {MAIN_DB}")
        sys.exit(1)

    run_id = args.run_id or get_latest_run_id(args.family)
    if not run_id:
        logger.error(f"No runs found for family '{args.family}'")
        sys.exit(1)

    logger.info(f"Analyzing run {run_id} for family '{args.family}'")

    # Get failures
    failures = get_failed_examples(run_id)
    logger.info(f"Found {len(failures)} failed examples")

    if not failures:
        logger.info("No failures to learn from. Exiting.")
        return

    # Cluster and extract
    clusters = cluster_by_error_signature(failures)
    logger.info(f"Clustered into {len(clusters)} error signatures")

    # Choose extraction method
    if args.use_llm:
        llm_service = _get_llm_service()
        if llm_service:
            logger.info("Using LLM-powered pattern extraction")
            patterns = extract_patterns_with_llm(clusters, args.family, llm_service)
        else:
            logger.warning("LLM unavailable, falling back to rule-based extraction")
            patterns = extract_patterns(clusters, args.family)
    else:
        patterns = extract_patterns(clusters, args.family)

    # Store
    stored = store_patterns(patterns, run_id, dry_run=args.dry_run)
    if not args.dry_run:
        logger.info(f"Stored {stored} new patterns")

    # Update performance
    if not args.dry_run and CATALOG_DB.exists():
        update_performance(args.family)

    # Summary
    print(f"\nAuto-Learn Summary")
    print(f"{'='*40}")
    print(f"Run: {run_id}")
    print(f"Extraction mode: {'LLM' if args.use_llm else 'Rule-based'}")
    print(f"Failures analyzed: {len(failures)}")
    print(f"Error clusters: {len(clusters)}")
    for sig, examples in clusters.items():
        print(f"  {sig}: {len(examples)} examples")
    print(f"Patterns extracted: {len(patterns)}")
    auto = sum(1 for p in patterns if p.get("auto_approved", False))
    executable = sum(1 for p in patterns if p.get("fix_code"))
    print(f"  Auto-approved: {auto}")
    print(f"  Executable (has fix_code): {executable}")
    print(f"  Needs review: {len(patterns) - auto}")


if __name__ == "__main__":
    main()
