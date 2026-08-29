"""PolicyDecisionPoint (TC-EPIC1-01) -- the single place capability decisions are computed.

Real WRITE_MARKDOWN, COMMIT_GIT, WRITE_ARTIFACT, and EXECUTE_CODE policy semantics
are registered via ``PolicyDecisionPoint.register_policy()`` by TC-EPIC1-02/03/04.
Before a policy is registered for a given capability, ``check()`` fails closed: it
returns ``Decision(allow=False, ...)``, never raises, and never allow-by-default --
this is the property the now-deleted ``check_provenance_enabled()``
(src/core/provenance_guard.py, removed in TC-EPIC1-05) notably lacked: it just
echoed back whatever boolean it was handed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from src.core.authority.capabilities import Capability


class PolicyDecisionDeniedError(Exception):
    """Raised by :meth:`PolicyDecisionPoint.require`, never by :meth:`check`."""

    def __init__(self, decision: "Decision") -> None:
        self.decision = decision
        super().__init__(f"{decision.capability.value} denied: {decision.reason} (policy_id={decision.policy_id})")


@dataclass(frozen=True)
class Decision:
    """Immutable result of a single PolicyDecisionPoint.check() call."""

    allow: bool
    reason: str
    policy_id: str
    capability: Capability
    resource: Optional[str] = None


# A policy function computes allow/reason/policy_id for one capability given the
# caller-supplied resource and context. It must be a pure function of its inputs
# (plus whatever config the PDP was constructed with) -- no ambient global state.
PolicyFunc = Callable[[Optional[str], Dict[str, Any]], "Decision"]


class PolicyDecisionPoint:
    """The one place every write/execute/commit/publish call site consults.

    Constructed with a config manager (or ``None`` for infrastructure-only use,
    e.g. this taskcard's own unit tests) and an optional database handle for
    audit recording. Real per-capability policy logic is registered by later
    taskcards via :meth:`register_policy`; capabilities with no registered
    policy fail closed.
    """

    def __init__(self, config_manager: Optional[Any] = None, database: Optional[Any] = None) -> None:
        self._config_manager = config_manager
        self._database = database
        self._policies: Dict[Capability, PolicyFunc] = {}

    def register_policy(self, capability: Capability, policy_func: PolicyFunc) -> None:
        """Register the real policy function for a capability (used by TC-EPIC1-02..06)."""
        self._policies[capability] = policy_func

    def check(
        self,
        capability: Capability,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Compute (and audit) the decision for one capability check.

        Never raises. A capability with no registered policy function returns a
        fail-closed Decision(allow=False, policy_id="no_policy_registered") --
        this is the fail-closed-by-default contract the negative controls in
        tests/test_authority_pdp.py verify.
        """
        context = context or {}
        run_id = context.get("run_id")

        # TC-EPIC1-04: for the two capabilities whose resource genuinely lives
        # under this repo's own artifacts/workspace/data roots (compiled
        # binaries, temp execution dirs), resolve the path first via
        # resolve_write_target() so a symlink/junction escape or UNC path is
        # caught before the registered policy even runs. WRITE_MARKDOWN is
        # deliberately NOT included here: markdown content lives in arbitrary,
        # externally-configured content roots (not under artifacts/workspace/
        # data/), so an allowlist restricted to internal repo directories would
        # incorrectly deny every real markdown write -- its path safety
        # continues to come from the existing assert_write_allowed()/
        # is_read_only_path() call already in markdown_service.py, unchanged.
        if capability in (Capability.WRITE_ARTIFACT, Capability.EXECUTE_CODE) and resource:
            from src.core.path_guard import resolve_write_target

            resolved = resolve_write_target(resource)
            if not resolved.allowed:
                decision = Decision(
                    allow=False,
                    reason=f"Path resolution denied: {resolved.reason}",
                    policy_id="path_guard.resolved_denied",
                    capability=capability,
                    resource=resource,
                )
                self._record(decision, run_id)
                return decision

        policy_func = self._policies.get(capability)
        if policy_func is None:
            decision = Decision(
                allow=False,
                reason=f"No policy registered for capability {capability.value!r}; failing closed.",
                policy_id="no_policy_registered",
                capability=capability,
                resource=resource,
            )
        else:
            decision = policy_func(resource, context)

        self._record(decision, run_id)
        return decision

    def require(
        self,
        capability: Capability,
        resource: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Decision:
        """Convenience wrapper: call :meth:`check` and raise if denied."""
        decision = self.check(capability, resource, context)
        if not decision.allow:
            raise PolicyDecisionDeniedError(decision)
        return decision

    def _record(self, decision: Decision, run_id: Optional[str]) -> None:
        """Record this decision to the authority_audit table, allow or deny alike."""
        if self._database is None:
            return
        self._database.record_authority_decision(
            capability=decision.capability.value,
            resource=decision.resource,
            decision="allow" if decision.allow else "deny",
            policy_id=decision.policy_id,
            run_id=run_id,
            reason=decision.reason,
        )
