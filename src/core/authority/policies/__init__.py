"""Real per-capability policy bodies, registered onto a PolicyDecisionPoint instance.

Kept out of pdp.py itself so the kernel (TC-EPIC1-01) stays infrastructure-only and
each capability's policy semantics (TC-EPIC1-02, TC-EPIC1-03, ...) can be reviewed,
tested, and evolved independently.
"""
