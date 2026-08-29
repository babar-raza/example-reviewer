"""Capability enum for the Authorization Kernel (TC-EPIC1-01).

A closed, explicit list of the gate-worthy actions in the pipeline. Deliberately
not string-based/dynamic: adding a new capability requires a visible diff here,
not a new ad hoc string appearing at some call site (which is exactly the pattern
that produced the 5 disagreeing markdown-write gates and 4 disagreeing commit
gates documented in FINDINGS_REGISTER.md F-014).
"""

from enum import Enum


class Capability(str, Enum):
    """Gate-worthy actions that must go through the PolicyDecisionPoint.

    Values are the ``policy_id`` prefix used in ``Decision.policy_id`` and in the
    ``authority_audit`` table's ``capability`` column, so keep them stable once
    committed -- a future rename requires a migration note, not a silent edit.
    """

    WRITE_MARKDOWN = "write_markdown"
    WRITE_ARTIFACT = "write_artifact"
    EXECUTE_CODE = "execute_code"
    COMMIT_GIT = "commit_git"
    PUSH_GIT = "push_git"
    PUBLISH_GIST = "publish_gist"
    CALL_LLM_EXTERNAL = "call_llm_external"
    CALL_LLM_LOCAL = "call_llm_local"
