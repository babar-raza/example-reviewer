"""COMMIT_GIT policy body (TC-EPIC1-03).

Collapses the 4 independent commit-authorization derivations documented in
reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md F-013:
  - src/cli/main.py:1116 (allow_commit=getattr(args, 'commit', False))
  - src/mcp_tools/tools.py:484 (hardcoded allow_commit=True -- THE BUG THIS CLOSES:
    this bypassed the family auto_commit gate unconditionally, since
    orchestrator.py's `if not allow_commit:` skip meant a hardcoded True never
    consulted family_config.auto_commit at all)
  - src/pipeline/orchestrator.py (commit_enabled = allow_commit or global_config.git.enabled)
  - src/pipeline/orchestrator.py (family_config.auto_commit gate, previously only
    consulted `if not allow_commit`)

into a single, pure function of (resource, context) -> Decision. THE KEY BEHAVIOR
CHANGE (documented in the taskcard as intentional security hardening, not a bug-
compatible migration): family_config.auto_commit is now consulted UNCONDITIONALLY,
even when cli_commit_flag/MCP explicitly requested a commit. An explicit commit
request no longer bypasses a family's declared "don't auto-commit me" safety switch.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.authority.capabilities import Capability
from src.core.authority.pdp import Decision


def commit_git_policy(resource: Optional[str], context: Dict[str, Any]) -> Decision:
    """Compute the COMMIT_GIT decision. ``resource`` is the family name.

    Expected context keys:
      - cli_commit_flag (bool): the --commit flag / MCP commit-tool request.
      - git_enabled (bool): global_config.git.enabled (default True upstream).
      - family_auto_commit (bool): family_config.auto_commit (default False
        upstream) -- ALWAYS consulted now, regardless of cli_commit_flag.
      - dry_run (bool): if True, deny regardless of the above (no commit in a
        dry run, matching pre-existing behavior at orchestrator.py's dry_run check).
    """
    family = resource
    cli_commit_flag = bool(context.get("cli_commit_flag", False))
    git_enabled = bool(context.get("git_enabled", False))
    family_auto_commit = bool(context.get("family_auto_commit", False))
    dry_run = bool(context.get("dry_run", False))

    if dry_run:
        return Decision(
            allow=False,
            reason="Dry run: git commit is never performed in a dry run.",
            policy_id="commit_git.dry_run",
            capability=Capability.COMMIT_GIT,
            resource=family,
        )

    commit_requested = cli_commit_flag or git_enabled
    if not commit_requested:
        return Decision(
            allow=False,
            reason="Commit not requested: no --commit flag and global_config.git.enabled is False.",
            policy_id="commit_git.not_requested",
            capability=Capability.COMMIT_GIT,
            resource=family,
        )

    # The behavioral fix: family_auto_commit is consulted UNCONDITIONALLY, even
    # when cli_commit_flag is explicitly True. This is what closes the MCP
    # hardcode bug (tools.py:484's allow_commit=True previously skipped this
    # check entirely via the old `if not allow_commit:` guard).
    if not family_auto_commit:
        return Decision(
            allow=False,
            reason=(
                f"Commit blocked: family {family!r} has auto_commit=False. "
                "An explicit --commit/MCP commit request does not override this "
                "safety switch (TC-EPIC1-03 intentionally removed that bypass -- "
                "see FINDINGS_REGISTER.md F-013). Set auto_commit=true in this "
                "family's config to allow commits."
            ),
            policy_id="commit_git.family_auto_commit_false",
            capability=Capability.COMMIT_GIT,
            resource=family,
        )

    return Decision(
        allow=True,
        reason=f"Commit authorized for family {family!r} (auto_commit=true, commit requested).",
        policy_id="commit_git.allowed",
        capability=Capability.COMMIT_GIT,
        resource=family,
    )
