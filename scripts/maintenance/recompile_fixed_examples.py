"""
Re-compile the 6 fixed examples to verify they now compile.
"""
import sys
import sqlite3
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import Database
from src.services.compilation_service import CompilationService
from src.core.config import load_family_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = r"C:\Users\prora\AppData\Local\ExampleReviewer\workspaces\20260124_093716\db\example_reviewer.db"
RUN_ID = "427b0788195264da"

FIXED_EXAMPLES = [
    "5707970e00a9f0e2",
    "1a67c64482727938",
    "9d556118e6063c54",
    "603983d0dadbfec6",
    "98026ca264a750da",
    "a1bff9ce1a8b7dae",
]


def recompile_examples():
    """Re-compile the fixed examples."""

    # Initialize services
    db = Database(DB_PATH)
    config = load_family_config("zip")
    compilation_service = CompilationService(config)

    compile_success = 0
    compile_failed = 0

    for example_id in FIXED_EXAMPLES:
        logger.info(f"\n{'='*80}")
        logger.info(f"Re-compiling example {example_id}")

        # Get compilable_code from database
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("""
            SELECT compilable_code
            FROM example_run_state
            WHERE example_id = ? AND run_id = ?
        """, (example_id, RUN_ID)).fetchone()
        conn.close()

        if not row or not row[0]:
            logger.error(f"No compilable_code found for {example_id}")
            compile_failed += 1
            continue

        code = row[0]
        logger.info(f"Code length: {len(code)} chars")

        # Compile
        try:
            result = compilation_service.compile_code(
                example_id=example_id,
                code=code,
                family="zip",
                run_id=RUN_ID,
                workspace_root=Path(r"C:\Users\prora\AppData\Local\ExampleReviewer\workspaces\20260124_093716\workspace")
            )

            if result and result.success:
                logger.info(f"✓ COMPILE SUCCESS for {example_id}")
                compile_success += 1

                # Update example_run_state status to COMPILED
                conn = sqlite3.connect(DB_PATH)
                conn.execute("""
                    UPDATE example_run_state
                    SET status = 'COMPILED'
                    WHERE example_id = ? AND run_id = ?
                """, (example_id, RUN_ID))
                conn.commit()
                conn.close()
            else:
                logger.error(f"✗ COMPILE FAILED for {example_id}")
                if result and result.error_messages:
                    for err in result.error_messages[:3]:
                        logger.error(f"  - {err}")
                compile_failed += 1

        except Exception as e:
            logger.error(f"✗ EXCEPTION compiling {example_id}: {e}", exc_info=True)
            compile_failed += 1

    logger.info(f"\n{'='*80}")
    logger.info(f"RECOMPILATION SUMMARY:")
    logger.info(f"  Success: {compile_success}/6")
    logger.info(f"  Failed:  {compile_failed}/6")

    return compile_success, compile_failed


if __name__ == "__main__":
    success, failed = recompile_examples()
    sys.exit(0 if failed <= 2 else 1)  # Accept ≤2 failures per checklist
