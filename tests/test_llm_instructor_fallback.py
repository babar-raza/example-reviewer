"""
Tests for LLM instructor fallback behavior.

Validates that the instructor fallback chain handles exceptions correctly
without raising UnboundLocalError (RCA-006).
"""

import pytest
from unittest.mock import patch, MagicMock

try:
    import instructor
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False


@pytest.mark.skipif(not INSTRUCTOR_AVAILABLE, reason="instructor not installed")
class TestInstructorFallbackChain:
    """Test that instructor fallback does not raise UnboundLocalError."""

    def test_instructor_start_defined_when_from_openai_fails(self):
        """
        RCA-006: If instructor.from_openai() raises, the except block must
        not crash with UnboundLocalError on _instructor_start.
        The fix moves _instructor_start assignment before from_openai().
        """
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("src.services.llm_service.OPENAI_AVAILABLE", True):
                with patch("src.services.llm_service.OpenAI") as mock_openai:
                    mock_openai.return_value = MagicMock()
                    from src.services.llm_service import LLMService

                    service = LLMService(
                        model="test-model",
                        api_key="test-key",
                        base_url="http://localhost:11434/v1",
                    )

                    with patch.object(
                        instructor,
                        "from_openai",
                        side_effect=RuntimeError("from_openai failed"),
                    ):
                        try:
                            service._review_with_instructor(
                                code_snippets=[
                                    {"code": "Console.WriteLine();", "example_id": "t1"}
                                ],
                                system_prompt="Test prompt",
                                family="zip",
                            )
                        except UnboundLocalError:
                            pytest.fail(
                                "_instructor_start was unbound in except block — "
                                "RCA-006 bug is NOT fixed"
                            )
                        except Exception:
                            # Any other exception is acceptable — the important
                            # thing is that UnboundLocalError did not occur.
                            pass
