"""Tests for TC-EPIC1-05: provenance_guard folded in as a first-class PDP precondition.

check_provenance_enabled() is deleted entirely (it added no value beyond echoing a
boolean); validate_provenance()/validate_batch_provenance() are unchanged and now
invoked directly from the WRITE_MARKDOWN policy body as a genuine precondition.
"""

from unittest.mock import MagicMock

import pytest

from src.core.authority import Capability, PolicyDecisionPoint
from src.core.authority.policies.markdown_write import write_markdown_policy
from src.core.models import ExampleStatus
from src.core.provenance_guard import ProvenanceViolationError, validate_batch_provenance


def _pdp() -> PolicyDecisionPoint:
    pdp = PolicyDecisionPoint()
    pdp.register_policy(Capability.WRITE_MARKDOWN, write_markdown_policy)
    return pdp


def _verified_example(example_id="ex-ok"):
    ex = MagicMock()
    ex.example_id = example_id
    ex.verified_code = "public class Foo {}"
    ex.status = ExampleStatus.VERIFIED
    return ex


def _unverified_example(example_id="ex-bad"):
    ex = MagicMock()
    ex.example_id = example_id
    ex.verified_code = None
    ex.status = ExampleStatus.DISCOVERED
    return ex


def test_write_markdown_denied_when_config_allows_but_provenance_fails():
    pdp = _pdp()
    decision = pdp.check(
        Capability.WRITE_MARKDOWN,
        resource="content/foo.md",
        context={"config_allow": True, "examples": [_unverified_example()]},
    )
    assert decision.allow is False
    assert "provenance" in decision.reason.lower() or decision.policy_id == "write_markdown.provenance_violation"


def test_write_markdown_denied_when_config_disallows_even_if_provenance_passes():
    """Config gate short-circuits FIRST -- a fully verified example does not
    override writes_enabled=False."""
    pdp = _pdp()
    decision = pdp.check(
        Capability.WRITE_MARKDOWN,
        resource="content/foo.md",
        context={"config_allow": False, "cli_override": False, "examples": [_verified_example()]},
    )
    assert decision.allow is False
    assert decision.policy_id == "write_markdown.writes_disabled"


def test_provenance_violation_error_never_escapes_pdp_check():
    pdp = _pdp()
    # Should not raise, even with a maximally-broken example.
    decision = pdp.check(
        Capability.WRITE_MARKDOWN,
        resource="content/foo.md",
        context={"config_allow": True, "examples": [_unverified_example(), _unverified_example("ex-bad-2")]},
    )
    assert decision.allow is False


def test_validate_batch_provenance_still_directly_callable():
    """Regression guard: the batch function's direct-call contract (outside the
    PDP) is unchanged -- callers other than the PDP can still use it directly."""
    signals = validate_batch_provenance([_verified_example()], require_verified=True)
    assert len(signals) == 1
    assert signals[0].example_id == "ex-ok"

    with pytest.raises(ProvenanceViolationError):
        validate_batch_provenance([_unverified_example()], require_verified=True)


def test_check_provenance_enabled_removed():
    """NEGATIVE CONTROL: the dead echo-function is actually gone, not just
    unused -- prevents any future code from accidentally reintroducing a call
    to it as if it were still a meaningful check."""
    with pytest.raises(ImportError):
        from src.core.provenance_guard import check_provenance_enabled  # noqa: F401


def test_hand_edited_markdown_cannot_fake_a_pass():
    """The concrete 'don't let hand-edited Markdown fake a pass' scenario: an
    example that was never compiled/verified (status=DISCOVERED) but has a
    forged verified_code string in memory must still be denied, because
    validate_provenance's status check runs independently of verified_code
    presence."""
    pdp = _pdp()
    forged = MagicMock()
    forged.example_id = "ex-forged"
    forged.verified_code = "// looks legit but was never actually verified"
    forged.status = ExampleStatus.DISCOVERED  # never passed the pipeline

    decision = pdp.check(
        Capability.WRITE_MARKDOWN,
        resource="content/foo.md",
        context={"config_allow": True, "examples": [forged]},
    )
    assert decision.allow is False
    assert decision.policy_id == "write_markdown.provenance_violation"
