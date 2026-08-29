"""Authorization Kernel (TC-EPIC1-01).

The single place capability decisions are computed, replacing the 5 independent
markdown-write and 4 independent commit-authorization derivations documented in
reports/investigation/20260829_124758_production_readiness/FINDINGS_REGISTER.md
(F-012, F-013, F-014). See src/core/authority/pdp.py for the design rationale.
"""

from src.core.authority.capabilities import Capability
from src.core.authority.pdp import Decision, PolicyDecisionDeniedError, PolicyDecisionPoint

__all__ = ["Capability", "Decision", "PolicyDecisionDeniedError", "PolicyDecisionPoint"]
