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

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent  # scripts/patterns/ -> scripts/ -> repo root
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

    # Known code transformers — auto-discovered from LearnedPatternsService registry
    # with fallback to hardcoded list if import fails
    _FALLBACK_TRANSFORMERS = {
        "fix_stream_disposal",
        "fix_rar_password",
        "fix_entries_string_index",
        "fix_placeholder_archives",
        "fix_placeholder_dirs",
        "fix_placeholder_passwords",
    }

    @classmethod
    def _discover_transformers(cls) -> set:
        """Auto-discover registered transformers from LearnedPatternsService."""
        try:
            from src.services.learned_patterns_service import LearnedPatternsService
            registered = set(LearnedPatternsService._transformers.keys())
            if registered:
                return registered
        except (ImportError, AttributeError):
            pass
        return cls._FALLBACK_TRANSFORMERS

    @property
    def KNOWN_TRANSFORMERS(self) -> set:
        """Lazily discover available transformers."""
        if not hasattr(self, "_cached_transformers"):
            self._cached_transformers = self._discover_transformers()
        return self._cached_transformers

    EXTRACTION_PROMPT = """Analyze these {count} failed C# code examples with error signature: {signature}

## Failed Examples:
{examples}

{catalog_context}

## Task:
Generate an EXECUTABLE fix pattern (not just a description).

## Fix Type Decision Tree:
1. IF error is CS0246/CS0103/CS0234 AND type exists in available namespaces:
   → Use fix_type="using_directive"
2. ELIF fix is simple text replacement (enum value, constant, method name):
   → Use fix_type="regex_replace"
3. ELIF fix requires known multi-step transformation:
   → Use fix_type="code_transform" (only if transformer exists)
4. ELSE (complex logic that needs LLM):
   → Use fix_type="llm_prompt"

## Output Schema (RETURN ONLY VALID JSON):
{{
    "fix_type": "using_directive|regex_replace|code_transform|llm_prompt",
    "fix_code": {{
        // SCHEMA VARIES BY FIX_TYPE - choose ONE:

        // For using_directive (missing type/namespace):
        "directive": "using Aspose.Words.Drawing;",
        "trigger_type": "Shape"

        // For regex_replace (text substitution):
        "pattern": "CompressionLevel\\.Normal",
        "replacement": "CompressionLevel.Optimal"

        // For code_transform (known transformation):
        "transformer": "fix_stream_disposal",
        "params": {{}}

        // For llm_prompt (complex fix):
        "prompt": "Fix {{error}} by {{description}}. Code: {{code}}",
        "system_prompt": "You are a C# code fixer."
    }},
    "confidence": 0.7,
    "fix_template": "Human-readable description",
    "example_before": "var level = CompressionLevel.Normal;",
    "example_after": "var level = CompressionLevel.Optimal;"
}}

## EXAMPLES:

### Example 1: using_directive (CS0246 - missing type)
{{
    "fix_type": "using_directive",
    "fix_code": {{
        "directive": "using Aspose.Zip.Saving;",
        "trigger_type": "ParallelOptions"
    }},
    "confidence": 0.9,
    "fix_template": "Add using directive for Aspose.Zip.Saving namespace",
    "example_before": "var opts = new ParallelOptions();",
    "example_after": "using Aspose.Zip.Saving;\\nvar opts = new ParallelOptions();"
}}

### Example 2: regex_replace (enum value correction)
{{
    "fix_type": "regex_replace",
    "fix_code": {{
        "pattern": "CompressionLevel\\.Normal",
        "replacement": "CompressionLevel.Optimal"
    }},
    "confidence": 0.85,
    "fix_template": "Replace CompressionLevel.Normal with CompressionLevel.Optimal",
    "example_before": "var level = CompressionLevel.Normal;",
    "example_after": "var level = CompressionLevel.Optimal;"
}}

### Example 3: code_transform (stream disposal)
{{
    "fix_type": "code_transform",
    "fix_code": {{
        "transformer": "fix_stream_disposal",
        "params": {{}}
    }},
    "confidence": 0.9,
    "fix_template": "Wrap stream in using statement",
    "example_before": "var ms = new MemoryStream();",
    "example_after": "using (var ms = new MemoryStream()) {{ ... }}"
}}

### Example 4: llm_prompt (complex logic fix)
{{
    "fix_type": "llm_prompt",
    "fix_code": {{
        "prompt": "Fix the null reference error in: {{code}}\\nError: {{error}}",
        "system_prompt": "Fix C# code. Return ONLY fixed code."
    }},
    "confidence": 0.5,
    "fix_template": "Fix null reference by adding null check",
    "example_before": "var x = obj.Property;",
    "example_after": "var x = obj?.Property ?? default;"
}}

## CRITICAL RULES:
1. ALWAYS choose the MOST SPECIFIC fix_type (prefer using_directive > regex_replace > code_transform > llm_prompt)
2. For CS0246/CS0103, ALWAYS use using_directive if type is in catalog
3. For regex_replace, ensure pattern is valid regex (escape special chars like \\.()[]{{}}+*?)
4. For code_transform, ONLY use transformers from: {transformers}
5. Keep confidence realistic: using_directive=0.8-0.9, regex_replace=0.7-0.9, code_transform=0.8-0.9, llm_prompt=0.3-0.6
6. Return ONLY the JSON object, no markdown fences, no explanations
"""

    def __init__(self, llm_service: Any, catalog=None):
        """
        Initialize with an LLM service instance.

        Args:
            llm_service: Instance of LLMService from src.services.llm_service
            catalog: Optional API catalog service for LLM context
        """
        self.llm_service = llm_service
        self.catalog = catalog

    def _build_catalog_context_for_extraction(self, error_signature: str) -> str:
        """Build compact catalog context for pattern extraction."""
        if not self.catalog or not self.catalog.is_loaded:
            return ""

        parts = []
        error_code = error_signature.split('_')[0]

        # For missing type errors: provide namespace list with sample types
        if error_code in ("CS0246", "CS0103", "CS0234"):
            namespaces = self.catalog.get_all_namespaces()
            if namespaces:
                parts.append("## Available API Namespaces (for using_directive):")
                # Limit to 15 namespaces to avoid token overflow
                for ns in namespaces[:15]:
                    # Try to get sample types from namespace
                    try:
                        types = self.catalog.get_types_in_namespace(ns)
                        if types:
                            sample_types = ", ".join(types[:5])  # Show up to 5 types
                            parts.append(f"  - {ns}: {sample_types}")
                        else:
                            parts.append(f"  - {ns}")
                    except Exception:
                        # If get_types_in_namespace doesn't exist, just show namespace
                        parts.append(f"  - {ns}")

        return "\n".join(parts) if parts else ""

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

        # Build catalog context if available
        catalog_context = self._build_catalog_context_for_extraction(signature)

        # Build base prompt with context
        prompt = self.EXTRACTION_PROMPT.format(
            count=len(examples),
            signature=signature,
            examples=examples_text,
            catalog_context=catalog_context,
            transformers=", ".join(sorted(self.KNOWN_TRANSFORMERS)),
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

    def _create_fallback_llm_prompt(
        self,
        data: Dict[str, Any],
        signature: str,
    ) -> Dict[str, Any]:
        """
        Create fallback llm_prompt fix_code from incomplete executable pattern.

        When LLM returns an invalid executable pattern, fall back to a generic
        llm_prompt that can still be useful.
        """
        description = data.get("fix_template", f"Fix {signature} error")
        example_before = data.get("example_before", "")
        example_after = data.get("example_after", "")

        # Build a reasonable prompt template
        prompt = f"""Fix the following C# code error: {signature}

Error context: {{error}}

Code with error:
```csharp
{{code}}
```

Expected fix: {description}
"""

        # Add examples if available
        if example_before and example_after:
            prompt += f"""
Example transformation:
BEFORE:
{example_before}

AFTER:
{example_after}
"""

        return {
            "prompt": prompt,
            "system_prompt": "You are a C# code fixer. Return ONLY the fixed code, no explanations.",
        }

    def _parse_llm_response(
        self,
        content: str,
        signature: str,
        family: str,
    ) -> Optional[Dict]:
        """Parse and validate the LLM response with executable pattern validation."""
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
        fix_type = data.get("fix_type", "llm_prompt")
        fix_code = data.get("fix_code", {})
        confidence = float(data.get("confidence", 0.5))

        # Validate fix_type is one of the allowed types
        if fix_type not in ("regex_replace", "using_directive", "code_transform", "llm_prompt", "template"):
            logger.warning(f"Invalid fix_type '{fix_type}', falling back to llm_prompt")
            fix_type = "llm_prompt"
            fix_code = self._create_fallback_llm_prompt(data, signature)

        # Validate fix_code structure based on fix_type
        elif fix_type == "using_directive":
            if not fix_code.get("directive"):
                logger.warning("using_directive missing 'directive', falling back to llm_prompt")
                fix_type = "llm_prompt"
                fix_code = self._create_fallback_llm_prompt(data, signature)
            else:
                # Valid using_directive - ensure directive has proper format
                directive = fix_code["directive"].strip()
                if not directive.startswith("using ") or not directive.endswith(";"):
                    logger.warning(f"Invalid directive format '{directive}', falling back")
                    fix_type = "llm_prompt"
                    fix_code = self._create_fallback_llm_prompt(data, signature)

        elif fix_type == "regex_replace":
            if not fix_code.get("pattern") or "replacement" not in fix_code:
                logger.warning("regex_replace missing 'pattern' or 'replacement', falling back")
                fix_type = "llm_prompt"
                fix_code = self._create_fallback_llm_prompt(data, signature)
            else:
                # Validate regex pattern is compilable
                try:
                    re.compile(fix_code["pattern"])
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{fix_code['pattern']}': {e}, falling back")
                    fix_type = "llm_prompt"
                    fix_code = self._create_fallback_llm_prompt(data, signature)

        elif fix_type == "code_transform":
            transformer = fix_code.get("transformer")
            if not transformer:
                logger.warning("code_transform missing 'transformer', falling back")
                fix_type = "llm_prompt"
                fix_code = self._create_fallback_llm_prompt(data, signature)
            elif transformer not in self.KNOWN_TRANSFORMERS:
                logger.warning(f"Unknown transformer '{transformer}', falling back to llm_prompt")
                logger.info(f"Known transformers: {', '.join(sorted(self.KNOWN_TRANSFORMERS))}")
                fix_type = "llm_prompt"
                fix_code = self._create_fallback_llm_prompt(data, signature)

        elif fix_type == "llm_prompt":
            # llm_prompt should have prompt in fix_code
            if not fix_code.get("prompt"):
                logger.warning("llm_prompt missing 'prompt', creating fallback")
                fix_code = self._create_fallback_llm_prompt(data, signature)

        elif fix_type == "template":
            # Template is legacy type - convert to llm_prompt
            logger.info("Converting template fix_type to llm_prompt")
            fix_type = "llm_prompt"
            fix_code = self._create_fallback_llm_prompt(data, signature)

        # Determine pattern_type from signature
        if signature.startswith("CS"):
            pattern_type = "compile_error"
        elif signature in ("PASSWORD_ISSUE", "MISSING_FILE", "MISSING_DIRECTORY"):
            pattern_type = "infra_blocked"
        else:
            pattern_type = "runtime_error"

        # Adjust auto_approved based on fix_type and confidence
        # Executable patterns get higher approval threshold
        if fix_type in ("using_directive", "regex_replace", "code_transform"):
            auto_approved = confidence >= 0.8
        else:
            # llm_prompt patterns require higher confidence for auto-approval
            auto_approved = confidence >= 0.85

        return {
            "family": family,
            "error_signature": signature,
            "pattern_type": pattern_type,
            "fix_type": fix_type,
            "fix_code": fix_code if fix_code else None,
            "fix_template": data.get("fix_template", f"LLM-generated fix for {signature}"),
            "confidence": min(0.9, max(0.1, confidence)),  # Clamp to 0.1-0.9
            "auto_approved": auto_approved,
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
    catalog=None,
) -> List[Dict]:
    """
    Extract patterns from all clusters using LLM.

    Args:
        clusters: Dict mapping signature -> list of failed examples
        family: Product family
        llm_service: LLM service instance
        catalog: Optional API catalog for LLM context

    Returns:
        List of patterns with executable fix_code
    """
    extractor = LLMPatternExtractor(llm_service, catalog=catalog)
    patterns = []

    for signature, examples in clusters.items():
        logger.info(f"Extracting pattern for {signature} ({len(examples)} examples)...")
        cluster_patterns = extractor.extract_patterns_with_llm(
            {"signature": signature, "examples": examples},
            family,
        )
        patterns.extend(cluster_patterns)

    return patterns


# Generic transformers that work across all Aspose families
GENERIC_TRANSFORMERS = {
    "fix_stream_disposal",
    "fix_placeholder_dirs",
    "fix_placeholder_passwords",
}


def _determine_scope(p: Dict) -> str:
    """Determine if a pattern should be family-scoped or global.

    Global patterns are applied to any family. Family patterns are restricted.

    Rules:
    - code_transform with generic transformer -> 'global'
    - using_directive with System.* namespace -> 'global'
    - using_directive with Aspose.* namespace -> 'family'
    - regex_replace -> 'family' (usually references family-specific APIs)
    - llm_prompt -> 'family' (prompts contain family context)
    - template -> 'family'
    """
    fix_type = p.get("fix_type", "template")
    fix_code = p.get("fix_code") or {}

    if fix_type == "code_transform":
        transformer = fix_code.get("transformer", "")
        if transformer in GENERIC_TRANSFORMERS:
            return "global"

    if fix_type == "using_directive":
        directive = fix_code.get("directive", "")
        if directive.startswith("using System"):
            return "global"
        return "family"

    return "family"


def _is_duplicate(conn: sqlite3.Connection, p: Dict) -> bool:
    """Check if a functionally equivalent pattern already exists.

    Deduplicates by (family, error_signature, fix_type):
    - template patterns: same triple = duplicate
    - executable patterns: also compare normalized fix_code JSON
    """
    family = p["family"]
    error_sig = p["error_signature"]
    fix_type = p.get("fix_type", "template")

    rows = conn.execute(
        """SELECT id, fix_code FROM learned_patterns
           WHERE family = ? AND error_signature = ? AND fix_type = ?
             AND (source IS NULL OR source NOT LIKE 'retired_%')""",
        (family, error_sig, fix_type),
    ).fetchall()

    if not rows:
        return False

    # Template patterns have no fix_code — same triple is enough
    if fix_type == "template":
        return True

    # Executable patterns: compare normalized fix_code JSON
    new_fix_code = json.dumps(p.get("fix_code"), sort_keys=True) if p.get("fix_code") else None
    for _row_id, existing_fix_code in rows:
        if not existing_fix_code and not new_fix_code:
            return True
        if existing_fix_code and new_fix_code:
            try:
                existing_normalized = json.dumps(json.loads(existing_fix_code), sort_keys=True)
                if existing_normalized == new_fix_code:
                    return True
            except json.JSONDecodeError:
                pass
    return False


def _validate_pattern_on_store(p: Dict, catalog: Optional[Any] = None) -> Optional[str]:
    """Validate a pattern before storing. Returns error message or None if valid.

    Checks:
    - regex_replace: pattern must compile
    - using_directive: namespace must exist in catalog (if available)
    """
    fix_type = p.get("fix_type", "template")
    fix_code = p.get("fix_code") or {}

    if fix_type == "regex_replace":
        pattern_str = fix_code.get("pattern", "")
        if pattern_str:
            try:
                re.compile(pattern_str)
            except re.error as e:
                return f"Invalid regex pattern '{pattern_str}': {e}"

    if fix_type == "using_directive" and catalog:
        directive = fix_code.get("directive", "")
        ns_match = re.match(r"using\s+([\w.]+);", directive)
        if ns_match:
            namespace = ns_match.group(1)
            # System.* namespaces are always valid (BCL)
            if not namespace.startswith("System"):
                known_ns = catalog.get_all_namespaces() if hasattr(catalog, "get_all_namespaces") else []
                if known_ns and namespace not in known_ns:
                    return f"Namespace '{namespace}' not found in API catalog"

    return None


def store_patterns(
    patterns: List[Dict],
    run_id: str,
    dry_run: bool = False,
    catalog: Optional[Any] = None,
) -> int:
    """Store patterns in the catalog database (supports V2 schema with fix_code).

    Args:
        patterns: List of pattern dicts to store
        run_id: Pipeline run ID for audit trail
        dry_run: If True, log but don't insert
        catalog: Optional API catalog for using_directive validation
    """
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
    skipped_dup = 0
    skipped_invalid = 0

    # Check if V3 scope column exists
    db_cols = [row[1] for row in conn.execute("PRAGMA table_info(learned_patterns)").fetchall()]
    has_scope = "scope" in db_cols

    for p in patterns:
        try:
            # Phase 1A: Deduplication guard
            if _is_duplicate(conn, p):
                skipped_dup += 1
                logger.debug(
                    f"Duplicate pattern skipped: {p['error_signature']} "
                    f"({p.get('fix_type', 'template')})"
                )
                continue

            # Phase 4A/4B: Validation guard
            validation_error = _validate_pattern_on_store(p, catalog=catalog)
            if validation_error:
                skipped_invalid += 1
                logger.warning(f"Skipping invalid pattern: {validation_error}")
                continue

            # Serialize fix_code to JSON if present
            fix_code_json = None
            if p.get("fix_code"):
                fix_code_json = json.dumps(p["fix_code"])

            # Phase 2B: Determine scope (family vs global)
            scope = _determine_scope(p)

            if has_scope:
                conn.execute(
                    """INSERT INTO learned_patterns
                       (family, pattern_type, error_signature, fix_template,
                        fix_type, fix_code, confidence, auto_approved, priority,
                        requires_llm, example_before, example_after, source, scope)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                        scope,
                    ),
                )
            else:
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

    if skipped_dup or skipped_invalid:
        logger.info(
            f"Pattern storage: {inserted} inserted, "
            f"{skipped_dup} duplicates skipped, "
            f"{skipped_invalid} invalid skipped"
        )
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
        from src.core.config import ConfigurationManager

        # Load config to get API key env var name
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()
        llm_config = global_config.llm

        # Check for API key using the configured env var name
        api_key_env_var = llm_config.api_key_env_var
        api_key = os.getenv(api_key_env_var)
        if not api_key:
            logger.warning(f"{api_key_env_var} not set, LLM extraction unavailable")
            return None

        # Initialize service with config parameters
        service = LLMService(
            provider=llm_config.provider,
            model=llm_config.model,
            api_key=api_key,
            base_url=llm_config.base_url,
            temperature=llm_config.temperature,
            max_retries=llm_config.max_retries,
            retry_backoff_seconds=llm_config.retry_backoff_seconds,
            timeout_seconds=llm_config.timeout_seconds,
        )
        if service.is_available():
            logger.info(f"LLM service initialized: {llm_config.provider}/{llm_config.model} at {llm_config.base_url}")
            return service
        logger.warning("LLM service not available")
        return None
    except ImportError as e:
        logger.warning(f"Could not import LLM service: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error initializing LLM service: {e}")
        return None


def review_patterns(family: str, auto_approve: bool = False) -> None:
    """
    Review pending patterns: show summary, auto-approve high performers.

    Queries pattern_performance table and auto-approves patterns that meet
    thresholds (score >= 0.8 AND applications >= 3). Retires patterns with
    score <= 0.1 AND applications >= 10.
    """
    from src.services.learned_patterns_service import LearnedPatternsService

    service = LearnedPatternsService(family, db_path=CATALOG_DB)
    conn = sqlite3.connect(str(CATALOG_DB))
    conn.row_factory = sqlite3.Row

    # Get all pending patterns with performance data
    rows = conn.execute(
        """
        SELECT lp.id, lp.error_signature, lp.fix_type, lp.fix_template,
               lp.confidence, lp.source,
               COALESCE(pp.times_applied, 0) as times_applied,
               COALESCE(pp.times_succeeded, 0) as times_succeeded,
               COALESCE(pp.success_rate, 0.0) as success_rate
        FROM learned_patterns lp
        LEFT JOIN pattern_performance pp ON lp.id = pp.pattern_id
        WHERE lp.family = ?
          AND lp.auto_approved = FALSE
          AND lp.source NOT LIKE 'retired_%'
        ORDER BY lp.fix_type, pp.success_rate DESC
        """,
        (family,),
    ).fetchall()

    if not rows:
        print(f"No pending patterns for family '{family}'.")
        conn.close()
        service.close()
        return

    print(f"\nPending patterns for '{family}': {len(rows)}")
    print(f"{'='*70}")

    approve_ids = []
    retire_ids = []

    for row in rows:
        applied = row["times_applied"]
        rate = row["success_rate"]
        status = ""

        # Auto-approve: high performance
        if applied >= 3 and rate >= 0.8:
            status = " [AUTO-APPROVE]"
            approve_ids.append(row["id"])
        # Retire: consistently failing
        elif applied >= 10 and rate <= 0.1:
            status = " [RETIRE]"
            retire_ids.append(row["id"])

        print(
            f"  #{row['id']:3d} {row['fix_type']:18s} {row['error_signature']:12s} "
            f"conf={row['confidence']:.2f} "
            f"perf={row['times_succeeded']}/{applied} ({rate:.0%})"
            f"{status}"
        )

    print(f"\n{'='*70}")
    print(f"Summary: {len(approve_ids)} auto-approve, {len(retire_ids)} retire, "
          f"{len(rows) - len(approve_ids) - len(retire_ids)} needs review")

    if auto_approve:
        if approve_ids:
            count = service.bulk_approve(approve_ids)
            print(f"Approved {count} patterns")
        if retire_ids:
            for pid in retire_ids:
                service.retire_pattern(pid, "low_performance")
            print(f"Retired {len(retire_ids)} patterns")
    else:
        if approve_ids or retire_ids:
            print("(Use --auto-approve to apply changes)")

    conn.close()
    service.close()


def main():
    parser = argparse.ArgumentParser(description="Auto-learn fix patterns from pipeline runs")
    parser.add_argument("--family", required=True, help="Product family")
    parser.add_argument("--run-id", help="Specific run ID (default: latest)")
    parser.add_argument("--dry-run", action="store_true", help="Print patterns without storing")
    parser.add_argument("--use-llm", action="store_true", help="Use LLM for intelligent pattern extraction (overrides config)")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM extraction (overrides config)")
    parser.add_argument("--retire-patterns", action="store_true", help="Force pattern retirement (overrides config enabled=false)")
    parser.add_argument("--no-retire", action="store_true", help="Skip pattern retirement (overrides config)")
    parser.add_argument("--review", action="store_true", help="Review pending patterns (show status, auto-approve/retire)")
    parser.add_argument("--auto-approve", action="store_true", help="Apply auto-approve/retire actions during --review")
    args = parser.parse_args()

    # Handle --review subcommand
    if args.review:
        if not CATALOG_DB.exists():
            logger.error(f"Catalog database not found: {CATALOG_DB}")
            sys.exit(1)
        review_patterns(args.family, auto_approve=args.auto_approve)
        return

    if not MAIN_DB.exists():
        logger.error(f"Main database not found: {MAIN_DB}")
        sys.exit(1)

    # Load global config to check auto_learn.use_llm
    use_llm_from_config = False
    try:
        from src.core.config import ConfigurationManager
        config_mgr = ConfigurationManager(
            config_dir=PROJECT_ROOT / "config" / "families",
            global_config_path=PROJECT_ROOT / "config" / "global.json"
        )
        global_config = config_mgr.load_global_config()
        use_llm_from_config = global_config.auto_learn.use_llm
        logger.info(f"Loaded config: auto_learn.use_llm = {use_llm_from_config}")
    except Exception as e:
        logger.warning(f"Could not load global config, defaulting to rule-based extraction: {e}")

    # Determine LLM usage: CLI flag overrides config
    if args.use_llm:
        use_llm = True
        llm_mode_source = "CLI override (--use-llm)"
    elif args.no_llm:
        use_llm = False
        llm_mode_source = "CLI override (--no-llm)"
    else:
        use_llm = use_llm_from_config
        llm_mode_source = "config (auto_learn.use_llm)"

    logger.info(f"LLM extraction mode: {use_llm} (source: {llm_mode_source})")

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

    # Load API catalog for LLM context
    catalog = None
    try:
        from src.services.api_catalog_service import APICatalogService
        catalog = APICatalogService(args.family)
        logger.info(f"Loaded API catalog for {args.family}")
    except Exception as e:
        logger.warning(f"Could not load API catalog: {e}")

    # Choose extraction method
    if use_llm:
        llm_service = _get_llm_service()
        if llm_service:
            logger.info("Using LLM-powered pattern extraction")
            patterns = extract_patterns_with_llm(clusters, args.family, llm_service, catalog=catalog)
        else:
            logger.warning("LLM unavailable, falling back to rule-based extraction")
            patterns = extract_patterns(clusters, args.family)
    else:
        logger.info("Using rule-based pattern extraction")
        patterns = extract_patterns(clusters, args.family)

    # Store (pass catalog for using_directive validation)
    stored = store_patterns(patterns, run_id, dry_run=args.dry_run, catalog=catalog)
    if not args.dry_run:
        logger.info(f"Stored {stored} new patterns")

    # Update performance
    if not args.dry_run and CATALOG_DB.exists():
        update_performance(args.family)

    # NEW: Retire old patterns (unless disabled by --no-retire)
    retirement_stats = None
    if not args.no_retire:
        try:
            # Load global config for retirement policy
            from src.core.config import ConfigurationManager
            from src.services.learned_patterns_service import LearnedPatternsService

            config_mgr = ConfigurationManager(
                config_dir=PROJECT_ROOT / "config" / "families",
                global_config_path=PROJECT_ROOT / "config" / "global.json"
            )
            global_config = config_mgr.load_global_config()
            retirement_policy = global_config.pattern_retirement

            # Override enabled if --retire-patterns flag
            if args.retire_patterns:
                retirement_policy.enabled = True
                logger.info("Retirement enabled by CLI flag (--retire-patterns)")

            # Run retirement if enabled (or forced by CLI)
            if retirement_policy.enabled:
                logger.info(f"Running pattern retirement (dry_run={retirement_policy.dry_run})...")
                learned_service = LearnedPatternsService(args.family, db_path=CATALOG_DB)
                retirement_stats = learned_service.retire_patterns(retirement_policy)
                logger.info(
                    f"Retirement complete: {retirement_stats['retired_count']} patterns retired "
                    f"({retirement_stats['candidates_evaluated']} candidates evaluated)"
                )
                learned_service.close()
            else:
                logger.debug("Pattern retirement disabled in config")

        except Exception as e:
            logger.warning(f"Pattern retirement failed: {e}")

    # Summary
    print(f"\nAuto-Learn Summary")
    print(f"{'='*40}")
    print(f"Run: {run_id}")
    print(f"Extraction mode: {'LLM' if use_llm else 'Rule-based'} ({llm_mode_source})")
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

    # NEW: Retirement summary
    if retirement_stats:
        print(f"\nPattern Retirement:")
        print(f"  Candidates evaluated: {retirement_stats['candidates_evaluated']}")
        print(f"  Patterns retired: {retirement_stats['retired_count']}")
        if retirement_stats['retired_count'] > 0:
            for p in retirement_stats['retired_patterns']:
                perf = p['performance']
                print(
                    f"    - Pattern {p['pattern_id']} ({p['error_signature']}): "
                    f"{perf['success_rate']:.1%} success ({perf['times_succeeded']}/{perf['times_applied']}), "
                    f"{perf['age_days']} days old"
                )


if __name__ == "__main__":
    main()
