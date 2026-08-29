"""
Pytest configuration and fixtures for Example Reviewer Pipeline tests.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def make_pdp(allow_writes: bool = False):
    """Build a PolicyDecisionPoint for tests that construct MarkdownUpdateService
    directly (TC-EPIC1-02 made ``pdp`` a required constructor parameter, replacing
    the old ``allow_markdown_write`` bool, so a missed fixture fails loudly with a
    constructor error instead of silently getting wrong behavior).

    allow_writes=True registers a WRITE_MARKDOWN policy that always allows (matching
    the old ``allow_markdown_write=True`` test fixtures); allow_writes=False leaves
    WRITE_MARKDOWN unregistered, which the kernel fails closed on by design
    (matching the old default ``allow_markdown_write=False``).
    """
    from src.core.authority import Capability, Decision, PolicyDecisionPoint

    pdp = PolicyDecisionPoint()
    if allow_writes:
        pdp.register_policy(
            Capability.WRITE_MARKDOWN,
            lambda resource, context: Decision(
                allow=True,
                reason="test fixture: writes allowed",
                policy_id="test.permissive",
                capability=Capability.WRITE_MARKDOWN,
                resource=resource,
            ),
        )
    return pdp


@pytest.fixture
def permissive_pdp():
    """A PolicyDecisionPoint whose WRITE_MARKDOWN check always allows."""
    return make_pdp(allow_writes=True)


@pytest.fixture
def denying_pdp():
    """A PolicyDecisionPoint whose WRITE_MARKDOWN check fails closed (no policy registered)."""
    return make_pdp(allow_writes=False)
