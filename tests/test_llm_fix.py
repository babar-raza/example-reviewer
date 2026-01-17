#!/usr/bin/env python3
"""Test LLM fix on a known failing example (opt-in)."""

import os
import sqlite3
from pathlib import Path

import pytest

from src.services.llm_service import LLMService

DB_PATH = Path("data/example_reviewer.db")
EXAMPLE_ID_PREFIX = "35e5a83b"

pytestmark = pytest.mark.integration


def _get_compilable_code():
    if not DB_PATH.exists():
        pytest.skip(
            f"Database not found at {DB_PATH}; set up example_reviewer.db first.",
            allow_module_level=True,
        )
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT compilable_code
            FROM example_records
            WHERE example_id LIKE ?
            """,
            (f"{EXAMPLE_ID_PREFIX}%",),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if not row:
        pytest.skip(
            f"Example {EXAMPLE_ID_PREFIX} not found in {DB_PATH}.",
            allow_module_level=True,
        )
    return row[0]


@pytest.mark.skipif(
    os.getenv("RUN_LLM_FIX_TEST") != "1",
    reason="Set RUN_LLM_FIX_TEST=1 to run live LLM fix test.",
)
def test_llm_fix_example():
    compilable_code = _get_compilable_code()
    print("=" * 80)
    print("ORIGINAL CODE")
    print("=" * 80)
    print(compilable_code)
    print()

    llm_service = LLMService(
        provider="ollama",
        model="qwen2.5-coder:7b",
        base_url="http://localhost:11434/v1",
        temperature=0.2,
        max_retries=1,
    )

    if not llm_service.is_available():
        pytest.skip("Ollama is not available at http://localhost:11434/v1.")

    print("=" * 80)
    print("LLM SERVICE STATUS")
    print("=" * 80)
    print(f"Available: {llm_service.is_available()}")
    print()

    error_context = """Exit Code: -1
Exception Type: InvalidOperationException
Exception Message: Cannot access a closed Stream.
Stderr: Unhandled exception. System.InvalidOperationException: Cannot access a closed Stream."""

    print("=" * 80)
    print("CALLING LLM FOR FIX")
    print("=" * 80)

    response = llm_service.fix_code(
        code=compilable_code,
        error_logs=error_context,
        context_type="runtime",
    )

    print(f"Success: {response.success}")
    print(f"Error: {response.error}")
    print(f"Content length: {len(response.content) if response.content else 0}")
    print()

    if response.content:
        print("=" * 80)
        print("LLM RESPONSE")
        print("=" * 80)
        print(response.content)
    else:
        print("No content in response!")

    assert response.success


if __name__ == "__main__":
    os.environ.setdefault("RUN_LLM_FIX_TEST", "1")
    raise SystemExit(pytest.main([__file__]))
