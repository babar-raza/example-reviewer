"""WRITE_MARKDOWN policy body (TC-EPIC1-02).

Collapses the 5 independent markdown-write authorization derivations documented in
reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md F-014:
  - src/core/config.py:583 (MarkdownWriteConfig.allow_markdown_write, default False)
  - src/pipeline/orchestrator.py:457 (pass-through)
  - src/pipeline/orchestrator.py:5083 (OR-based override formula -- a DIFFERENT formula
    than line 457's, which is exactly the fragmentation bug this policy closes)
  - src/services/markdown_service.py:164-189 (a third re-check)
  - src/core/provenance_guard.py:116-137 (check_provenance_enabled, folded in as an
    inline precondition per this taskcard; a proper composable hook is TC-EPIC1-05)

into a single, pure function of (resource, context) -> Decision.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.authority.capabilities import Capability
from src.core.authority.pdp import Decision
from src.core.provenance_guard import check_provenance_enabled


def write_markdown_policy(resource: Optional[str], context: Dict[str, Any]) -> Decision:
    """Compute the WRITE_MARKDOWN decision.

    Expected context keys (all optional, default to the safe/deny-leaning value):
      - config_allow (bool): global_config.markdown_write.allow_markdown_write, read
        fresh by the caller before each check() call so a mid-run config change is
        honored (per TC-EPIC1-02's proposed change, point 5).
      - cli_override (bool): the --allow-md-write flag / allow_md_write parameter.
      - use_workspace_copy (bool): whether writes go to workspace copies rather than
        originals -- passed through to check_provenance_enabled() unchanged.
    """
    config_allow = bool(context.get("config_allow", False))
    cli_override = bool(context.get("cli_override", False))
    use_workspace_copy = bool(context.get("use_workspace_copy", False))

    writes_enabled = config_allow or cli_override

    if not writes_enabled:
        return Decision(
            allow=False,
            reason=(
                "Markdown writes not enabled: global_config.markdown_write.allow_markdown_write "
                "is False and no --allow-md-write override was supplied."
            ),
            policy_id="write_markdown.writes_disabled",
            capability=Capability.WRITE_MARKDOWN,
            resource=resource,
        )

    # Inline provenance precondition (TC-EPIC1-02 sequencing note): this preserves
    # today's check_provenance_enabled() gate exactly. It answers "should provenance
    # be enforced for this write", not "did this specific example pass provenance" --
    # per-example validation (validate_provenance) still runs in
    # MarkdownUpdateService.update_markdown_file() as it does today; TC-EPIC1-05 is
    # what turns this into a first-class composable PDP precondition.
    provenance_will_be_enforced = check_provenance_enabled(writes_enabled, use_workspace_copy)

    return Decision(
        allow=True,
        reason=(
            "Markdown writes enabled (config_allow=%s, cli_override=%s); "
            "provenance enforcement=%s." % (config_allow, cli_override, provenance_will_be_enforced)
        ),
        policy_id="write_markdown.enabled",
        capability=Capability.WRITE_MARKDOWN,
        resource=resource,
    )
