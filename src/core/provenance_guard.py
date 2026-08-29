"""
Provenance Guard for Markdown Updates.

Ensures that all markdown (.md) updates are backed by verified examples
from the pipeline's verify→fix→verify loop, preventing manual edits
that bypass validation.

CRITICAL: This module prevents the anti-pattern of "manually editing
content .md files just to pass reviews" by requiring provenance signals.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..core.models import ExampleRecord, ExampleStatus

logger = logging.getLogger(__name__)


class ProvenanceViolationError(Exception):
    """
    Raised when attempting to update markdown without proper provenance.

    This error indicates that a .md update was attempted but cannot be
    verified as originating from the pipeline's verify→fix→verify loop.
    """
    pass


@dataclass
class ProvenanceSignal:
    """
    Provenance signal for a markdown update.

    This represents the evidence that an update is legitimate:
    - example_id: Links to the ExampleRecord in the database
    - verification_status: The status of the example (must be VERIFIED or MD_UPDATED)
    - source_description: Human-readable description of where the code came from
    """
    example_id: str
    verification_status: ExampleStatus
    source_description: str
    verified_code_hash: Optional[str] = None


def validate_provenance(
    example: ExampleRecord,
    require_verified: bool = True,
) -> ProvenanceSignal:
    """
    Validate that an example has proper provenance for markdown updates.

    Args:
        example: The ExampleRecord to validate
        require_verified: If True, require example to be in VERIFIED or MD_UPDATED status

    Returns:
        ProvenanceSignal with validation details

    Raises:
        ProvenanceViolationError: If provenance validation fails
    """
    # Check 1: Example must have verified code
    if not example.verified_code:
        raise ProvenanceViolationError(
            f"Example {example.example_id} has no verified_code. "
            f"Cannot update markdown without verified code from pipeline."
        )

    # Check 2: Example status must indicate verification
    if require_verified and example.status not in (ExampleStatus.VERIFIED, ExampleStatus.MD_UPDATED):
        raise ProvenanceViolationError(
            f"Example {example.example_id} has status {example.status.value}, "
            f"but only VERIFIED or MD_UPDATED examples can update markdown files. "
            f"Status indicates example has not passed verification pipeline."
        )

    # Check 3: Build source description for provenance tracking
    source_description = _build_source_description(example)

    # Build and return provenance signal
    return ProvenanceSignal(
        example_id=example.example_id,
        verification_status=example.status,
        source_description=source_description,
        verified_code_hash=_compute_code_hash(example.verified_code) if example.verified_code else None,
    )


def validate_batch_provenance(
    examples: List[ExampleRecord],
    require_verified: bool = True,
) -> List[ProvenanceSignal]:
    """
    Validate provenance for multiple examples (batch validation).

    Args:
        examples: List of ExampleRecords to validate
        require_verified: If True, require all examples to be VERIFIED or MD_UPDATED

    Returns:
        List of ProvenanceSignals for all examples

    Raises:
        ProvenanceViolationError: If any example fails provenance validation
    """
    signals = []
    for example in examples:
        signal = validate_provenance(example, require_verified=require_verified)
        signals.append(signal)
    return signals


def _build_source_description(example: ExampleRecord) -> str:
    """
    Build human-readable source description for provenance tracking.

    Args:
        example: ExampleRecord to describe

    Returns:
        Description string suitable for logs and artifacts
    """
    parts = [
        f"example_id={example.example_id[:16]}...",
        f"status={example.status.value}",
    ]

    if example.file_path:
        parts.append(f"file={Path(example.file_path).name}")

    if example.location:
        parts.append(f"block={example.location.block_index}")

    # Add code availability context
    if example.compilable_code:
        parts.append("compilable=yes")

    if example.verified_code:
        parts.append("verified=yes")

    return " ".join(parts)


def _compute_code_hash(code: str) -> str:
    """
    Compute hash of verified code for provenance tracking.

    Args:
        code: Code string to hash

    Returns:
        SHA256 hash (first 16 characters)
    """
    import hashlib
    return hashlib.sha256(code.encode('utf-8')).hexdigest()[:16]


def generate_provenance_report(
    signals: List[ProvenanceSignal],
    file_path: str,
) -> Dict[str, Any]:
    """
    Generate provenance report for markdown update.

    This can be written as an artifact (e.g., content_changes.json)
    to provide audit trail for markdown updates.

    Args:
        signals: List of ProvenanceSignals from the update
        file_path: Path to the markdown file being updated

    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "file": file_path,
        "examples_updated": len(signals),
        "provenance": [
            {
                "example_id": sig.example_id,
                "status": sig.verification_status.value,
                "source": sig.source_description,
                "code_hash": sig.verified_code_hash,
            }
            for sig in signals
        ],
    }
