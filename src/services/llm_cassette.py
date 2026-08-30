"""VCR-style request/response cassette mechanism for LLM calls (TC-EPIC3-03).

Gives CI a way to run against pre-recorded LLM request/response pairs with
zero live network dependency, instead of relying on ad hoc per-test mocking
scattered across the test suite. Deliberately hand-rolled rather than
adopting vcrpy: the request shape LLMService.complete() needs to key on is a
small, uniform tuple (model, messages, temperature, seed, max_tokens), not
arbitrary HTTP -- a general-purpose HTTP-level VCR library would need as much
adapter code as this whole file already is, for no material benefit, and
hand-rolling keeps this change dependency-free, consistent with
circuit_breaker.py's own "no external dependencies" precedent in this
codebase.

Two modes, both driven by CassetteMode:
  RECORD:  the real request is made; the (request, response) pair is
           serialized to a fixture file keyed by a hash of the request.
  REPLAY:  the real request is never made. The recorded response is returned
           for a matching request; a request with no matching fixture raises
           CassetteMissError immediately -- it never silently falls through
           to a live call, since a silent live-call fallback would defeat
           the entire purpose of CI hermeticity.

Cassette files are plain JSON, one fixture per request-hash, under a
directory the caller controls. They record metadata (model, temperature,
seed, the message list, response content) -- never API keys or auth headers,
since keys never appear in message/parameter payloads to begin with (they
live in HTTP client auth headers, entirely outside what this module ever
sees or serializes).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class CassetteMode(str, Enum):
    RECORD = "record"
    REPLAY = "replay"


class CassetteMissError(Exception):
    """Raised in REPLAY mode when no fixture matches the request.

    Never silently falls back to a live call -- see module docstring. A
    caller seeing this should either record a fixture first (CassetteMode.RECORD)
    or check that the request's model/messages/temperature/seed/max_tokens
    match exactly what was recorded.
    """

    def __init__(self, key: str, cassette_dir: Path) -> None:
        self.key = key
        self.cassette_dir = cassette_dir
        super().__init__(
            f"No cassette fixture found for request {key!r} in {cassette_dir}. "
            "Record a fixture first (CassetteMode.RECORD), or verify the request "
            "parameters match exactly what was recorded."
        )


def _canonical_request(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    seed: Optional[int],
    max_tokens: int,
) -> Dict[str, Any]:
    """The exact fields a cassette keys and matches a request on."""
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "seed": seed,
        "max_tokens": max_tokens,
    }


def request_key(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    seed: Optional[int],
    max_tokens: int,
) -> str:
    """Stable hash of the request shape -- the cassette fixture's filename stem."""
    canonical = _canonical_request(model, messages, temperature, seed, max_tokens)
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


@dataclass
class LlmCassette:
    """Record or replay LLM request/response pairs against a fixture directory."""

    cassette_dir: Path
    mode: CassetteMode

    def __post_init__(self) -> None:
        self.cassette_dir = Path(self.cassette_dir)
        if self.mode == CassetteMode.RECORD:
            self.cassette_dir.mkdir(parents=True, exist_ok=True)

    def _fixture_path(self, key: str) -> Path:
        return self.cassette_dir / f"{key}.json"

    def replay(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        seed: Optional[int],
        max_tokens: int,
    ) -> Dict[str, Any]:
        """Return the recorded response dict for a matching request.

        Raises CassetteMissError if no fixture matches -- never makes a
        network call and never returns a stale/mismatched response.
        """
        key = request_key(model, messages, temperature, seed, max_tokens)
        path = self._fixture_path(key)
        if not path.exists():
            raise CassetteMissError(key, self.cassette_dir)
        fixture = json.loads(path.read_text(encoding="utf-8"))
        return fixture["response"]

    def record(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        seed: Optional[int],
        max_tokens: int,
        response: Dict[str, Any],
    ) -> Path:
        """Persist a (request, response) pair to a fixture file. Returns the path written."""
        key = request_key(model, messages, temperature, seed, max_tokens)
        path = self._fixture_path(key)
        fixture = {
            "request": _canonical_request(model, messages, temperature, seed, max_tokens),
            "response": response,
        }
        path.write_text(json.dumps(fixture, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def has_fixture(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        seed: Optional[int],
        max_tokens: int,
    ) -> bool:
        """Non-raising existence check, useful for tests/tooling."""
        key = request_key(model, messages, temperature, seed, max_tokens)
        return self._fixture_path(key).exists()
