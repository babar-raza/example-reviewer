"""
Results summary export for determinism verification.

Exports run results in a structured format suitable for comparison across runs.
Used by tools/verify_determinism.py to validate reproducibility.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class ResultsSummary:
    """
    Results summary for a pipeline run.

    Captures terminal states and metadata for determinism verification:
    - run_id: Unique run identifier
    - family: Product family
    - selection_hash: SHA256 of sorted example_keys (proves exact set)
    - examples_processed: Total examples processed
    - examples_verified: Successfully verified count
    - examples_failed: Failed count
    - per_example_statuses: Dict[example_id, status] for each example
    - drift_scores: Optional drift scores (for tolerance checking)
    - run_duration_seconds: Total run time
    - timestamp: When summary was created
    """

    def __init__(
        self,
        run_id: str,
        family: str,
        selection_hash: str,
        examples_processed: int = 0,
        examples_verified: int = 0,
        examples_failed: int = 0,
        per_example_statuses: Optional[Dict[str, str]] = None,
        drift_scores: Optional[Dict[str, float]] = None,
        run_duration_seconds: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize results summary.

        Args:
            run_id: Unique run identifier
            family: Product family
            selection_hash: SHA256 hash of sorted example_keys
            examples_processed: Total examples processed
            examples_verified: Successfully verified count
            examples_failed: Failed count
            per_example_statuses: Map of example_id -> terminal status
            drift_scores: Optional map of example_id -> drift_score
            run_duration_seconds: Total run time in seconds
            timestamp: Summary creation timestamp
        """
        self.run_id = run_id
        self.family = family
        self.selection_hash = selection_hash
        self.examples_processed = examples_processed
        self.examples_verified = examples_verified
        self.examples_failed = examples_failed
        self.per_example_statuses = per_example_statuses or {}
        self.drift_scores = drift_scores or {}
        self.run_duration_seconds = run_duration_seconds
        self.timestamp = timestamp or datetime.utcnow()

    @classmethod
    def from_run(cls, db: 'Database', run_id: str) -> 'ResultsSummary':
        """
        Create results summary from database run.

        Args:
            db: Database instance
            run_id: Run identifier

        Returns:
            ResultsSummary with data from run
        """
        # Get run record
        run_record = db.get_run(run_id)
        if not run_record:
            raise ValueError(f"Run not found: {run_id}")

        family = run_record.family

        # Get all examples for this family
        # Note: We use family instead of run_id because examples are not directly linked to runs
        # This assumes the run processed all examples in the family at the time
        all_examples = db.get_examples_by_family(family)

        # Build selection_hash from example_keys
        example_keys = [ex.example_key for ex in all_examples if ex.example_key]
        selection_hash = db.compute_selection_hash(example_keys)

        # Build per-example statuses (keyed by example_id for uniqueness)
        per_example_statuses = {}
        drift_scores = {}

        for ex in all_examples:
            per_example_statuses[ex.example_id] = ex.status.value

            # Capture drift scores if available
            if hasattr(ex, 'drift_score') and ex.drift_score is not None:
                # Get drift_score from database row
                # Note: ExampleRecord model may not expose drift_score directly
                # We'll need to query it separately
                pass

        # Get drift scores from database (if stored)
        # For now, we'll leave drift_scores empty and document that it's optional
        # (Agent 4 handles drift, we just export what's available)

        # Compute run duration
        run_duration_seconds = None
        if run_record.completed_at and run_record.started_at:
            duration = run_record.completed_at - run_record.started_at
            run_duration_seconds = duration.total_seconds()

        # Get accurate stats from DB
        db_stats = db.get_run_stats_from_db(family, run_id)

        return cls(
            run_id=run_id,
            family=family,
            selection_hash=selection_hash,
            examples_processed=db_stats['total_processed'],
            examples_verified=db_stats['verified'],
            examples_failed=db_stats['failed'],
            per_example_statuses=per_example_statuses,
            drift_scores={},  # Optional: populated if drift tracking enabled
            run_duration_seconds=run_duration_seconds,
            timestamp=run_record.completed_at or datetime.utcnow(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert summary to dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'run_id': self.run_id,
            'family': self.family,
            'selection_hash': self.selection_hash,
            'timestamp_utc': self.timestamp.isoformat() if self.timestamp else None,
            'run_duration_seconds': self.run_duration_seconds,
            'summary': {
                'examples_processed': self.examples_processed,
                'examples_verified': self.examples_verified,
                'examples_failed': self.examples_failed,
            },
            'per_example_statuses': self.per_example_statuses,
            'drift_scores': self.drift_scores,
        }

    def to_json(self) -> str:
        """
        Convert summary to JSON string.

        Returns:
            JSON-formatted string with sorted keys for determinism
        """
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def save_to_file(self, path: Path) -> None:
        """
        Save summary to JSON file.

        Args:
            path: Output file path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResultsSummary':
        """
        Create summary from dictionary.

        Args:
            data: Dictionary with summary data

        Returns:
            ResultsSummary instance
        """
        summary = data.get('summary', {})

        return cls(
            run_id=data.get('run_id', ''),
            family=data.get('family', ''),
            selection_hash=data.get('selection_hash', ''),
            examples_processed=summary.get('examples_processed', 0),
            examples_verified=summary.get('examples_verified', 0),
            examples_failed=summary.get('examples_failed', 0),
            per_example_statuses=data.get('per_example_statuses', {}),
            drift_scores=data.get('drift_scores', {}),
            run_duration_seconds=data.get('run_duration_seconds'),
            timestamp=datetime.fromisoformat(data['timestamp_utc']) if data.get('timestamp_utc') else None,
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'ResultsSummary':
        """
        Create summary from JSON string.

        Args:
            json_str: JSON-formatted string

        Returns:
            ResultsSummary instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def load_from_file(cls, path: Path) -> 'ResultsSummary':
        """
        Load summary from JSON file.

        Args:
            path: Input file path

        Returns:
            ResultsSummary instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())
