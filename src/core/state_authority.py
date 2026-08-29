"""State Authority (TC-EPIC2-01) -- the single sanctioned entry point for changing
an example's status.

Closes Root Cause 2 (state fragmentation) documented in
reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md:
``Database.update_example_status()`` (src/core/database.py) issues a raw
``UPDATE example_run_state SET status = ...`` with no prior-status read and no
legality check, and is called directly from ~53 sites in
``src/pipeline/orchestrator.py`` plus a since-corrected direct in-memory
``.status =`` assignment in ``src/pipeline/error_router.py``. Nothing today
prevents, for example, an example jumping straight from ``DISCOVERED`` to
``COMMITTED``.

``StateAuthority`` does not reinvent transition legality: it constructs a scratch
``ExampleRecord`` and calls its existing (currently-dead-code)
``can_transition_to()`` (src/core/models.py), so this module and ``models.py``
can never define two different transition tables that silently disagree.
``Database.update_example_status()`` remains the sole low-level writer --
``StateAuthority`` is a thin validating wrapper in front of it, not a
replacement for it. The companion CI script,
``scripts/validation/check_no_raw_status_writes.py``, is what actually prevents
new code from bypassing this module going forward (TC-EPIC2-02 migrates the
existing 53+1 bypassing call sites).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from src.core.models import ExampleRecord, ExampleStatus

if TYPE_CHECKING:
    from src.core.database import Database


class IllegalTransitionError(Exception):
    """Raised by :meth:`StateAuthority.transition` when the attempted
    ``from_status -> to_status`` change is not present in
    ``ExampleRecord.can_transition_to()``'s table -- including the case where no
    prior ``example_run_state`` row exists at all (``from_status`` is ``None``),
    since legality cannot be determined without a known current state.

    Never silently swallowed or turned into a no-op: the whole point of this
    module is that an illegal status change is a raised, visible failure, not
    the previous raw-``UPDATE`` behavior of writing anything over anything.
    """

    def __init__(
        self,
        example_id: str,
        run_id: str,
        from_status: Optional[ExampleStatus],
        to_status: ExampleStatus,
    ) -> None:
        self.example_id = example_id
        self.run_id = run_id
        self.from_status = from_status
        self.to_status = to_status
        from_label = from_status.value if from_status is not None else "<no example_run_state row>"
        super().__init__(
            f"Illegal transition for example {example_id!r} (run {run_id!r}): "
            f"{from_label} -> {to_status.value} is not a valid transition."
        )


@dataclass(frozen=True)
class TransitionResult:
    """Result of a successful :meth:`StateAuthority.transition` call.

    Only ever returned on success -- an illegal transition raises
    :class:`IllegalTransitionError` instead of returning a result (per this
    taskcard's core behavioral fix: illegal transitions must be a loud
    failure, not a silently-returned "blocked" value a caller could ignore).
    ``illegal_attempt_blocked`` is therefore always ``False`` on a value
    actually returned by ``transition()``; it is kept on this dataclass so a
    caller that catches ``IllegalTransitionError`` and wants to build its own
    result object has a matching shape to build one with.
    """

    success: bool
    from_status: Optional[ExampleStatus]
    to_status: ExampleStatus
    illegal_attempt_blocked: bool = False


# example_id/file_path values are never persisted or read back -- can_transition_to()
# only inspects self.status. Kept fixed and clearly non-real so a scratch object
# accidentally leaking into a real code path is immediately recognizable.
_SCRATCH_FAMILY = "_state_authority_scratch"
_SCRATCH_FILE_PATH = "_state_authority_scratch"


class StateAuthority:
    """The only sanctioned entry point for changing an example's persisted status.

    Wraps a :class:`~src.core.database.Database` instance. Construct one per
    ``Orchestrator`` (or test), passing the same ``db`` the orchestrator already
    holds -- ``StateAuthority`` does not own its own connection.
    """

    def __init__(self, db: "Database") -> None:
        self.db = db

    def transition(
        self,
        example_id: str,
        run_id: str,
        to_status: ExampleStatus,
        failure_reason: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        evidence_ref: Optional[str] = None,
    ) -> TransitionResult:
        """Validate and perform one status transition, or raise.

        Reads the current status via ``Database.get_example_run_status()``,
        validates the transition using ``ExampleRecord.can_transition_to()``
        (reused, not reimplemented), writes via ``Database.update_example_status()``
        on success, and records a ``status_transitions`` audit row either way --
        a blocked attempt is recorded (``to_status`` with whatever ``from_status``
        was found, possibly ``None``) before the exception is raised, so the
        audit trail shows attempted-and-blocked transitions, not just successful
        ones.
        """
        from_status = self.db.get_example_run_status(run_id, example_id)
        timestamp = datetime.now(timezone.utc).isoformat()

        if from_status is None or not self._can_transition(from_status, to_status):
            self.db.record_status_transition(
                example_id=example_id,
                run_id=run_id,
                from_status=from_status.value if from_status is not None else None,
                to_status=to_status.value,
                evidence_ref=evidence_ref,
                timestamp=timestamp,
            )
            raise IllegalTransitionError(example_id, run_id, from_status, to_status)

        self.db.update_example_status(
            example_id,
            to_status,
            failure_reason=failure_reason,
            run_id=run_id,
            escalation_reason=escalation_reason,
        )
        self.db.record_status_transition(
            example_id=example_id,
            run_id=run_id,
            from_status=from_status.value,
            to_status=to_status.value,
            evidence_ref=evidence_ref,
            timestamp=timestamp,
        )
        return TransitionResult(success=True, from_status=from_status, to_status=to_status)

    @staticmethod
    def _can_transition(from_status: ExampleStatus, to_status: ExampleStatus) -> bool:
        """Delegate to ExampleRecord.can_transition_to() on a scratch instance,
        so this module's notion of "legal" can never drift from models.py's."""
        scratch = ExampleRecord(family=_SCRATCH_FAMILY, file_path=_SCRATCH_FILE_PATH, status=from_status)
        return scratch.can_transition_to(to_status)

    # -------------------------------------------------------------------
    # Named convenience methods (TC-EPIC2-01) -- give orchestrator.py's call
    # sites (migrated in TC-EPIC2-02) a small, self-documenting API instead of
    # raw ExampleStatus.X juggling at every call site. Statuses with no
    # dedicated method here (COMPILE_FAILED, RUNTIME_FAILED, NEEDS_REVIEW,
    # MD_UPDATED) go through transition() directly -- see TC-EPIC2-01.md.
    # -------------------------------------------------------------------

    def mark_compiled(
        self, example_id: str, run_id: str, evidence_ref: Optional[str] = None
    ) -> TransitionResult:
        return self.transition(example_id, run_id, ExampleStatus.COMPILABLE, evidence_ref=evidence_ref)

    def mark_verified(
        self, example_id: str, run_id: str, evidence_ref: Optional[str] = None
    ) -> TransitionResult:
        return self.transition(example_id, run_id, ExampleStatus.VERIFIED, evidence_ref=evidence_ref)

    def mark_committed(
        self, example_id: str, run_id: str, evidence_ref: Optional[str] = None
    ) -> TransitionResult:
        return self.transition(example_id, run_id, ExampleStatus.COMMITTED, evidence_ref=evidence_ref)

    def mark_infra_blocked(
        self,
        example_id: str,
        run_id: str,
        failure_reason: Optional[str] = None,
        evidence_ref: Optional[str] = None,
    ) -> TransitionResult:
        return self.transition(
            example_id, run_id, ExampleStatus.INFRA_BLOCKED, failure_reason=failure_reason, evidence_ref=evidence_ref
        )

    def mark_final_review_passed(
        self, example_id: str, run_id: str, evidence_ref: Optional[str] = None
    ) -> TransitionResult:
        return self.transition(example_id, run_id, ExampleStatus.FINAL_REVIEW_PASSED, evidence_ref=evidence_ref)

    def mark_final_review_failed(
        self,
        example_id: str,
        run_id: str,
        failure_reason: Optional[str] = None,
        evidence_ref: Optional[str] = None,
    ) -> TransitionResult:
        return self.transition(
            example_id, run_id, ExampleStatus.FINAL_REVIEW_FAILED, failure_reason=failure_reason, evidence_ref=evidence_ref
        )
