"""
Debug script: Run a single example through the pipeline step-by-step.
Tracks database state after each phase to understand the compilation/runtime discrepancy.
"""

import logging
from pathlib import Path
from src.core.database import Database
from src.core.config import ConfigurationManager
from src.pipeline.orchestrator import PipelineOrchestrator
from src.core.models import ExampleStatus

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def inspect_database_state(db: Database, example_id: str, phase: str):
    """Inspect and print database state for an example."""
    print(f"\n{'='*80}")
    print(f"DATABASE STATE AFTER: {phase}")
    print(f"{'='*80}")

    # Get example record
    with db.get_connection() as conn:
        cursor = conn.cursor()

        example = cursor.execute(
            "SELECT example_id, status, original_code, compilable_code, verified_code, "
            "failure_reason FROM example_records WHERE example_id = ?",
            (example_id,)
        ).fetchone()

        if example:
            print(f"Example ID: {example[0]}")
            print(f"Status: {example[1]}")
            print(f"Has original_code: {bool(example[2])}")
            print(f"Has compilable_code: {bool(example[3])}")
            print(f"Has verified_code: {bool(example[4])}")
            print(f"Failure reason: {example[5][:100] if example[5] else None}")
        else:
            print(f"Example {example_id} NOT FOUND in database")

        # Check compile attempts
        compile_attempts = cursor.execute(
            "SELECT timestamp, success, error_messages FROM compile_attempts "
            "WHERE example_id = ? ORDER BY timestamp",
            (example_id,)
        ).fetchall()

        print(f"\nCompile Attempts: {len(compile_attempts)}")
        for i, attempt in enumerate(compile_attempts):
            print(f"  Attempt {i+1} ({attempt[0]}): success={attempt[1]}, error={attempt[2][:80] if attempt[2] else None}")

        # Check runtime attempts
        runtime_attempts = cursor.execute(
            "SELECT timestamp, success, exit_code, stderr FROM runtime_attempts "
            "WHERE example_id = ? ORDER BY timestamp",
            (example_id,)
        ).fetchall()

        print(f"\nRuntime Attempts: {len(runtime_attempts)}")
        for i, attempt in enumerate(runtime_attempts):
            print(f"  Attempt {i+1} ({attempt[0]}): success={attempt[1]}, exit_code={attempt[2]}, error={attempt[3][:80] if attempt[3] else None}")

    print(f"{'='*80}\n")

def main():
    # Initialize
    config_manager = ConfigurationManager()
    global_config = config_manager.load_global_config()

    db = Database(global_config.database_path)

    # Pick one of the failed examples from previous investigation
    # Using the inline snippet example that had path not found error
    target_example_id = "1a78833310063754"

    print(f"\n{'#'*80}")
    print(f"RUNNING SINGLE EXAMPLE DEBUG: {target_example_id}")
    print(f"{'#'*80}\n")

    # Get initial state
    inspect_database_state(db, target_example_id, "INITIAL STATE")

    # Get the example details
    with db.get_connection() as conn:
        cursor = conn.cursor()

        example = cursor.execute(
            "SELECT example_id, family, file_path, source_type, original_code, status "
            "FROM example_records WHERE example_id = ?",
            (target_example_id,)
        ).fetchone()

        if not example:
            print(f"ERROR: Example {target_example_id} not found in database")
            return

        print(f"Example Details:")
        print(f"  Family: {example[1]}")
        print(f"  File: {example[2]}")
        print(f"  Source Type: {example[3]}")
        print(f"  Status: {example[5]}")
        print(f"  Has Code: {bool(example[4])}")

    # Create orchestrator
    orchestrator = PipelineOrchestrator(
        family="zip",
        limit=None,
        force_rerun=True,  # Force rerun to see the phases
        skip_discovery=True,  # Skip discovery, work with existing example
        skip_compilation=False,
        skip_runtime=False,
        skip_markdown_update=True,
        skip_final_review=True,
    )

    print("\n" + "="*80)
    print("RUNNING COMPILATION PHASE")
    print("="*80)

    # Run just compilation
    try:
        # Get the example to process
        with db.get_connection() as conn:
            cursor = conn.cursor()
            examples = cursor.execute(
                "SELECT example_id, family, file_path, source_type, original_code, compilable_code "
                "FROM example_records WHERE example_id = ?",
                (target_example_id,)
            ).fetchall()

        if examples:
            # Process compilation for this example
            result = orchestrator._run_compilation_phase(
                examples=[(ex[0], ex[1], ex[2], ex[3], ex[4], ex[5]) for ex in examples],
                config=config_manager.get_family_config("zip")
            )
            print(f"\nCompilation phase result: {result}")
    except Exception as e:
        print(f"ERROR during compilation: {e}")
        import traceback
        traceback.print_exc()

    inspect_database_state(db, target_example_id, "AFTER COMPILATION")

    print("\n" + "="*80)
    print("RUNNING RUNTIME PHASE")
    print("="*80)

    # Run runtime
    try:
        result = orchestrator._run_runtime_phase(
            examples=[(ex[0], ex[1], ex[2], ex[3]) for ex in examples],
            config=config_manager.get_family_config("zip")
        )
        print(f"\nRuntime phase result: {result}")
    except Exception as e:
        print(f"ERROR during runtime: {e}")
        import traceback
        traceback.print_exc()

    inspect_database_state(db, target_example_id, "AFTER RUNTIME")

    print("\n" + "#"*80)
    print("DEBUG RUN COMPLETE")
    print("#"*80)

if __name__ == "__main__":
    main()
