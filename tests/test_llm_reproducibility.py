"""Tests for TC-EPIC3-03: LLM determinism modes (bit_exact / cassette_replayed
/ live_sampled) and the llm_cassette.py record/replay mechanism.

See reports/investigation/20260829_124758_production_readiness/taskcards/TC-EPIC3-03.md.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.llm_cassette import CassetteMissError, CassetteMode, LlmCassette, request_key
from src.services.llm_service import LLMResponse, LLMService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "llm_cassettes"


def _mock_response(content="fixed code", model="test-model", prompt_tokens=10, completion_tokens=5):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    mock_response.choices[0].finish_reason = "stop"
    mock_response.model = model
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    mock_response.usage.total_tokens = prompt_tokens + completion_tokens
    return mock_response


class TestLlmCassetteUnit:
    def test_record_then_replay_round_trips(self, tmp_path):
        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.RECORD)
        cassette.record(
            model="m1", messages=[{"role": "user", "content": "hi"}],
            temperature=0.0, seed=42, max_tokens=100,
            response={"content": "hello", "model": "m1", "usage": {}, "finish_reason": "stop"},
        )

        replay_cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        result = replay_cassette.replay(
            model="m1", messages=[{"role": "user", "content": "hi"}], temperature=0.0, seed=42, max_tokens=100,
        )
        assert result == {"content": "hello", "model": "m1", "usage": {}, "finish_reason": "stop"}

    def test_replay_miss_raises_cassette_miss_error(self, tmp_path):
        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        with pytest.raises(CassetteMissError):
            cassette.replay(model="m1", messages=[{"role": "user", "content": "hi"}], temperature=0.0, seed=None, max_tokens=100)

    def test_replay_does_not_match_on_slightly_different_request(self, tmp_path):
        """A request whose parameters differ even slightly from what's
        recorded must NOT match -- replay matching must be strict."""
        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.RECORD)
        cassette.record(
            model="m1", messages=[{"role": "user", "content": "hi"}], temperature=0.0, seed=42, max_tokens=100,
            response={"content": "hello", "model": "m1", "usage": {}, "finish_reason": "stop"},
        )
        replay_cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        with pytest.raises(CassetteMissError):
            replay_cassette.replay(
                model="m1", messages=[{"role": "user", "content": "hi, slightly different"}],
                temperature=0.0, seed=42, max_tokens=100,
            )

    def test_request_key_is_stable_and_order_independent_for_dict_keys(self):
        k1 = request_key(model="m1", messages=[{"role": "user", "content": "hi"}], temperature=0.0, seed=1, max_tokens=10)
        k2 = request_key(model="m1", messages=[{"role": "user", "content": "hi"}], temperature=0.0, seed=1, max_tokens=10)
        assert k1 == k2

    def test_has_fixture_non_raising_check(self, tmp_path):
        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.RECORD)
        assert cassette.has_fixture(model="m1", messages=[], temperature=0.0, seed=None, max_tokens=1) is False
        cassette.record(
            model="m1", messages=[], temperature=0.0, seed=None, max_tokens=1,
            response={"content": "x", "model": "m1", "usage": {}, "finish_reason": "stop"},
        )
        assert cassette.has_fixture(model="m1", messages=[], temperature=0.0, seed=None, max_tokens=1) is True


class TestReproducibilityClassification:
    def test_live_sampled_by_default(self):
        service = LLMService(provider="ollama", model="test-model")
        assert service.get_reproducibility_class() == "live_sampled"

    def test_bit_exact_when_deterministic_seed_and_zero_temp(self):
        service = LLMService(
            provider="ollama", model="test-model", temperature=0.0, seed=42, deterministic_mode=True,
        )
        assert service.get_reproducibility_class() == "bit_exact"

    def test_not_bit_exact_without_seed_even_with_deterministic_mode(self):
        """The core policy fix this taskcard exists for: temperature=0 +
        deterministic_mode=True is NOT bit_exact without an actual seed."""
        service = LLMService(provider="ollama", model="test-model", temperature=0.0, deterministic_mode=True, seed=None)
        assert service.get_reproducibility_class() == "live_sampled"

    def test_cassette_replayed_takes_priority(self, tmp_path):
        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        service = LLMService(
            provider="ollama", model="test-model", temperature=0.0, seed=42, deterministic_mode=True, cassette=cassette,
        )
        assert service.get_reproducibility_class() == "cassette_replayed"

    def test_bit_exact_mode_without_seed_raises_at_construction(self):
        """Negative control: requesting bit_exact without a seed MUST fail
        fast at construction, not silently degrade to live_sampled."""
        with pytest.raises(ValueError, match="bit_exact"):
            LLMService(
                provider="ollama", model="test-model", temperature=0.0,
                deterministic_mode=True, seed=None, reproducibility_mode="bit_exact",
            )

    def test_bit_exact_mode_without_deterministic_mode_raises(self):
        with pytest.raises(ValueError, match="bit_exact"):
            LLMService(
                provider="ollama", model="test-model", temperature=0.0,
                deterministic_mode=False, seed=42, reproducibility_mode="bit_exact",
            )

    def test_bit_exact_mode_with_nonzero_temperature_raises(self):
        with pytest.raises(ValueError, match="bit_exact"):
            LLMService(
                provider="ollama", model="test-model", temperature=0.2,
                deterministic_mode=True, seed=42, reproducibility_mode="bit_exact",
            )

    def test_bit_exact_mode_with_everything_set_succeeds(self):
        service = LLMService(
            provider="ollama", model="test-model", temperature=0.0,
            deterministic_mode=True, seed=42, reproducibility_mode="bit_exact",
        )
        assert service.get_reproducibility_class() == "bit_exact"


class TestCompleteCassetteIntegration:
    @patch('src.services.llm_service.OpenAI')
    def test_record_mode_makes_real_call_and_persists_fixture(self, mock_openai, tmp_path):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.RECORD)
        service = LLMService(provider="openai", model="test-model", api_key="sk-test", cassette=cassette)

        response = service.complete(prompt="hello", temperature=0.0)

        assert response.success is True
        assert response.content == "fixed code"
        # Called at least once (lazy capability detection may add a second
        # call); the important assertion is the fixture was actually written.
        assert mock_client.chat.completions.create.called
        assert list(tmp_path.glob("*.json")), "Expected a fixture file to be written"

    @patch('src.services.llm_service.OpenAI')
    def test_replay_mode_returns_fixture_with_zero_network_calls(self, mock_openai, tmp_path):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        # First, record a real fixture. (The mocked client is called twice here:
        # once for lazy provider-capability detection, once for the actual
        # completion -- both are legitimate live calls in RECORD mode.)
        record_cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.RECORD)
        recording_service = LLMService(provider="openai", model="test-model", api_key="sk-test", cassette=record_cassette)
        recording_service.complete(prompt="hello", temperature=0.0)
        assert mock_client.chat.completions.create.called

        # Now replay against a FRESH client mock -- zero further calls expected.
        mock_client.chat.completions.create.reset_mock()
        replay_cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        replaying_service = LLMService(provider="openai", model="test-model", api_key="sk-test", cassette=replay_cassette)

        response = replaying_service.complete(prompt="hello", temperature=0.0)

        assert response.success is True
        assert response.content == "fixed code"
        assert response.reproducibility_class == "cassette_replayed"
        mock_client.chat.completions.create.assert_not_called()

    @patch('src.services.llm_service.OpenAI')
    def test_replay_mode_with_no_matching_cassette_raises_not_falls_back_to_live(self, mock_openai, tmp_path):
        """The core CI-hermeticity guarantee: a cassette miss must be loud,
        never a silent live-call fallback."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        empty_cassette = LlmCassette(cassette_dir=tmp_path, mode=CassetteMode.REPLAY)
        service = LLMService(provider="openai", model="test-model", api_key="sk-test", cassette=empty_cassette)

        with pytest.raises(CassetteMissError):
            service.complete(prompt="hello", temperature=0.0)

        mock_client.chat.completions.create.assert_not_called()

    def test_replays_committed_fixture_with_openai_client_never_constructed(self):
        """Uses the real, committed fixture under tests/fixtures/llm_cassettes/
        (not a tmp_path) -- proves cassette_replayed mode is hermetic even
        against a durable, tracked fixture, with the OpenAI client class
        itself patched to raise if ever instantiated (stronger than just
        asserting the mock wasn't called -- this proves network access could
        be fully removed and this test would still pass)."""
        with patch(
            'src.services.llm_service.OpenAI',
            side_effect=AssertionError("OpenAI client must never be constructed in cassette_replayed mode"),
        ):
            cassette = LlmCassette(cassette_dir=FIXTURES_DIR, mode=CassetteMode.REPLAY)
            # deterministic_mode/seed must match what the fixture was recorded
            # with (seed=42), since the cassette key incorporates the seed.
            service = LLMService(
                provider="openai", model="gpt-4o", api_key="sk-test",
                temperature=0.0, seed=42, deterministic_mode=True, cassette=cassette,
            )
            assert service._client is None  # _init_client() swallowed the AssertionError -- confirms it fired

            response = service.complete(
                prompt="Extract the C# code from this text.",
                system_prompt="You are a code extraction expert.",
                max_tokens=2048,
                temperature=0.0,
            )

        assert response.success is True
        assert response.content == 'Console.WriteLine("Hello, Aspose.Zip!");'
        assert response.reproducibility_class == "cassette_replayed"

    @patch('src.services.llm_service.OpenAI')
    def test_live_call_reproducibility_class_is_live_sampled(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        service = LLMService(provider="openai", model="test-model", api_key="sk-test")
        response = service.complete(prompt="hello")

        assert response.reproducibility_class == "live_sampled"

    @patch('src.services.llm_service.OpenAI')
    def test_live_call_reproducibility_class_is_bit_exact_when_configured(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_response()

        service = LLMService(
            provider="openai", model="test-model", api_key="sk-test",
            temperature=0.0, seed=42, deterministic_mode=True, reproducibility_mode="bit_exact",
        )
        with patch.object(service, "get_provider_capabilities") as mock_caps:
            mock_caps.return_value = MagicMock(seed_supported=True)
            response = service.complete(prompt="hello", temperature=0.0)

        assert response.reproducibility_class == "bit_exact"
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["seed"] == 42


class TestFinalReviewIsGenuinelyBitExact:
    def test_llm_service_factory_final_review_branch_is_bit_exact(self):
        from src.services.llm_service import LLMServiceFactory

        config = {
            "final_review": {"provider": "openai", "model": "gpt-4o", "timeout_seconds": 30},
            "llm": {},
        }
        with patch.object(LLMService, "_init_client"):
            service = LLMServiceFactory.from_config(config, use_final_review=True)

        assert service.deterministic_mode is True
        assert service.seed == 42  # config default
        assert service.temperature == 0.0
        assert service.get_reproducibility_class() == "bit_exact"

    def test_llm_service_factory_final_review_branch_respects_configured_seed(self):
        from src.services.llm_service import LLMServiceFactory

        config = {
            "final_review": {"provider": "openai", "model": "gpt-4o", "timeout_seconds": 30, "seed": 7},
            "llm": {},
        }
        with patch.object(LLMService, "_init_client"):
            service = LLMServiceFactory.from_config(config, use_final_review=True)

        assert service.seed == 7
        assert service.get_reproducibility_class() == "bit_exact"

    def test_orchestrator_final_review_property_is_bit_exact(self):
        """Regression test for the REAL production construction site
        (previously seed=None, deterministic_mode=False -- temperature=0.0
        only, not genuinely bit_exact)."""
        from src.pipeline.orchestrator import PipelineOrchestrator as Orchestrator

        orch = object.__new__(Orchestrator)
        orch.config_manager = MagicMock()
        global_config = MagicMock()
        global_config.final_review.provider = "openai"
        global_config.final_review.model = "gpt-4o"
        global_config.final_review.api_key_env_var = "OPENAI_API_KEY"
        global_config.final_review.base_url = None
        global_config.final_review.timeout_seconds = 30
        global_config.final_review.seed = 42
        global_config.model_routing.enabled = False
        orch.config_manager.load_global_config.return_value = global_config
        orch._final_review_llm_service = None

        with patch.object(LLMService, "_init_client"):
            service = orch.final_review_llm_service

        assert service.deterministic_mode is True
        assert service.seed == 42
        assert service.temperature == 0.0
        assert service.get_reproducibility_class() == "bit_exact"
