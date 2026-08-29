"""WRITE_MARKDOWN policy body (TC-EPIC1-02, provenance precondition TC-EPIC1-05).

Collapses the 5 independent markdown-write authorization derivations documented in
reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md F-014:
  - src/core/config.py:583 (MarkdownWriteConfig.allow_markdown_write, default False)
  - src/pipeline/orchestrator.py:457 (pass-through)
  - src/pipeline/orchestrator.py:5083 (OR-based override formula -- a DIFFERENT formula
    than line 457's, which is exactly the fragmentation bug this policy closes)
  - src/services/markdown_service.py:164-189 (a third re-check)
  - src/core/provenance_guard.py's now-DELETED check_provenance_enabled(), which just
    echoed back allow_markdown_write (its use_workspace_copy parameter was entirely
    unused despite the docstring's claim otherwise -- a discovered dead-parameter bug,
    closed by removal rather than perpetuated)

into a single, pure function of (resource, context) -> Decision.

TC-EPIC1-05 adds a genuine provenance PRECONDITION: when context carries an
`examples` list (the examples a caller is about to write to a markdown file),
validate_batch_provenance() runs as part of this same check() call, and a
ProvenanceViolationError is caught and converted to a Decision instead of
escaping to the caller. When no `examples` are supplied (e.g. the file-level
authorization check in MarkdownUpdateService._validate_write_allowed(), which
doesn't have specific example objects in scope), this precondition is simply
skipped -- the config/cli_override gate above is still fully enforced either way.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.authority.capabilities import Capability
from src.core.authority.pdp import Decision
from src.core.provenance_guard import ProvenanceViolationError, validate_batch_provenance


def write_markdown_policy(resource: Optional[str], context: Dict[str, Any]) -> Decision:
    """Compute the WRITE_MARKDOWN decision.

    Expected context keys (all optional, default to the safe/deny-leaning value):
      - config_allow (bool): global_config.markdown_write.allow_markdown_write, read
        fresh by the caller before each check() call so a mid-run config change is
        honored (per TC-EPIC1-02's proposed change, point 5).
      - cli_override (bool): the --allow-md-write flag / allow_md_write parameter.
      - use_workspace_copy (bool): whether writes go to workspace copies rather than
        originals. Recorded for diagnostic purposes only (the pre-TC-EPIC1-05
        check_provenance_enabled() accepted this parameter but never actually used
        it either -- provenance is enforced identically regardless).
      - examples (list[ExampleRecord], optional): if provided, a genuine
        per-example provenance precondition runs via validate_batch_provenance()
        (TC-EPIC1-05). If omitted, this precondition is skipped (the caller is
        presumed to run its own provenance check separately, or none is needed
        for this particular call, e.g. a pre-write path-authorization check with
        no specific examples in scope yet).
    """
    config_allow = bool(context.get("config_allow", False))
    cli_override = bool(context.get("cli_override", False))
    examples = context.get("examples")

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

    # Provenance precondition (TC-EPIC1-05): runs AFTER the config gate, so a
    # config-disabled write short-circuits above without the unnecessary
    # examples/DB work implied by provenance validation -- only reached once
    # writes are already known to be enabled.
    if examples is not None:
        try:
            validate_batch_provenance(examples, require_verified=True)
        except ProvenanceViolationError as e:
            return Decision(
                allow=False,
                reason=str(e),
                policy_id="write_markdown.provenance_violation",
                capability=Capability.WRITE_MARKDOWN,
                resource=resource,
            )

    return Decision(
        allow=True,
        reason=(
            "Markdown writes enabled (config_allow=%s, cli_override=%s)%s."
            % (
                config_allow,
                cli_override,
                f"; provenance validated for {len(examples)} example(s)" if examples is not None else "",
            )
        ),
        policy_id="write_markdown.enabled",
        capability=Capability.WRITE_MARKDOWN,
        resource=resource,
    )
