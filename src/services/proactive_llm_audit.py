"""
Proactive LLM audit — top slice of the LLM sandwich.

Runs BEFORE the first compile attempt. Detects known-bad semantic patterns in
code using article intent + family review hints loaded from
config/families/{family}_review_hints.json.

The service is generic: all family specialisation is in the hints JSON file.
Only hints that match via ``pattern`` (substring in code) and optional
``context`` (substring in intent/markdown) are activated.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProactiveAuditIssue:
    """A single issue detected by the proactive LLM audit."""

    hint_id: str
    issue_type: str   # "outdated_api" | "semantic_misuse" | "missing_required_property"
    description: str
    correction: str
    severity: str = "error"  # "error" | "warning"


def load_family_hints(family: str, config_dir: str = "config/families") -> List[Dict[str, Any]]:
    """Load review hints for *family* from ``{config_dir}/{family}_review_hints.json``.

    Returns an empty list if the file does not exist or cannot be parsed.
    """
    path = Path(config_dir) / f"{family}_review_hints.json"
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception as exc:
        logger.warning("proactive_audit: failed to load hints for '%s': %s", family, exc)
        return []


def _filter_hints(
    hints: List[Dict[str, Any]],
    code: str,
    article_intent: str,
    markdown_snippet: str,
) -> List[Dict[str, Any]]:
    """Return only the hints whose ``pattern`` / ``context`` filters match."""
    context_blob = "\n".join([article_intent, markdown_snippet[:2000]]).lower()
    matched: List[Dict[str, Any]] = []
    for hint in hints:
        pattern = hint.get("pattern")
        if pattern and pattern not in code:
            continue
        ctx_key = hint.get("context", "").lower()
        if ctx_key and ctx_key not in context_blob:
            continue
        matched.append(hint)
    return matched


def run_proactive_audit(
    code: str,
    article_intent: str,
    section_heading: str,
    family_hints: List[Dict[str, Any]],
    llm_service,
) -> List[ProactiveAuditIssue]:
    """Run the top-slice LLM audit and return a list of detected issues.

    Only issues with *severity* == ``"error"`` are typically actioned by the
    caller; ``"warning"`` issues are logged and ignored.

    Args:
        code:           Current C# source code of the example.
        article_intent: Compact intent string (title + description + steps).
        section_heading: Markdown heading immediately above the code block.
        family_hints:   Pre-filtered list of hint dicts from
                        ``{family}_review_hints.json``.
        llm_service:    Initialised ``LLMService`` instance used for the LLM
                        call.  Must expose a ``complete()`` method that returns
                        an object with a ``.content`` attribute.

    Returns:
        List of :class:`ProactiveAuditIssue`.  Empty if the LLM reports no
        issues or if the LLM call fails.
    """
    if not family_hints or not code.strip():
        return []

    hints_text = "\n".join(
        "- [{id}] {desc} "
        "(detect if code contains: {kw}) "
        "-> Correction: {corr}".format(
            id=h.get("id", "?"),
            desc=h.get("issue_description", h.get("hint", "")),
            kw=", ".join(h.get("detection_keywords", [])),
            corr=h.get("correction", ""),
        )
        for h in family_hints
    )

    prompt = (
        "Review the following C# code for known issues.\n\n"
        f"Article intent: {article_intent or 'Not specified'}\n"
        f"Section: {section_heading or 'Not specified'}\n\n"
        "Known problematic patterns to check for:\n"
        f"{hints_text}\n\n"
        "Code to review:\n"
        "```csharp\n"
        f"{code}\n"
        "```\n\n"
        "Return a JSON array of detected issues. Each issue must have:\n"
        '- "hint_id": the id from the pattern list above\n'
        '- "issue_type": one of "outdated_api", "semantic_misuse", "missing_required_property"\n'
        '- "description": brief description of what is wrong in this specific code\n'
        '- "correction": the specific fix needed for this code\n'
        '- "severity": "error" (must fix) or "warning" (informational)\n\n'
        "Return [] if no issues are found. Return ONLY JSON, no other text."
    )

    system_prompt = (
        "You are a C# code reviewer. Return ONLY a JSON array matching the requested schema. "
        "Do NOT include markdown fences or explanatory prose."
    )

    try:
        response = llm_service.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0,
            max_tokens=1200,
        )
        raw_text: str = response.content if hasattr(response, "content") else str(response)

        # Extract the JSON array from the response
        json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if not json_match:
            logger.debug("proactive_audit: LLM returned no JSON array; response=%r", raw_text[:200])
            return []

        issues_data = json.loads(json_match.group())
        results: List[ProactiveAuditIssue] = []
        for item in issues_data:
            if not isinstance(item, dict):
                continue
            results.append(
                ProactiveAuditIssue(
                    hint_id=str(item.get("hint_id", "")),
                    issue_type=str(item.get("issue_type", "semantic_misuse")),
                    description=str(item.get("description", "")),
                    correction=str(item.get("correction", "")),
                    severity=str(item.get("severity", "error")),
                )
            )
        return results

    except Exception as exc:
        logger.warning("proactive_audit: LLM call failed: %s", exc)
        return []
