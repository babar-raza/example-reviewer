"""
LLM Service for Example Reviewer Pipeline.
Supports OpenAI-compatible models as required by the spec.
"""

import os
import re
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import instructor
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False

from .llm_contracts import ReviewResponse, ReviewIssue, IssueType, Severity
from ..pipeline.error_complexity_classifier import ErrorComplexityClassifier

try:
    from .circuit_breaker import CircuitBreaker, build_circuit_breaker_from_config
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

logger = logging.getLogger(__name__)


def _is_transient_error(error: Exception) -> bool:
    """Return True for network/server errors that should trip the circuit breaker.

    Returns False for permanent errors (auth, validation) that must NOT trip the
    circuit — we don't want a bad API key to cause Ollama failover.
    """
    permanent_types = (ValueError, KeyError, AttributeError, TypeError)
    if isinstance(error, permanent_types):
        return False
    err_str = str(error).lower()
    # 401/403 are auth errors — permanent, don't trip circuit
    if "401" in err_str or "403" in err_str or "authentication" in err_str:
        return False
    return True  # Default: treat as transient (connection, timeout, 5xx, etc.)


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    latency_ms: int
    success: bool = True
    error: Optional[str] = None
    raw_prompt: Optional[str] = None  # For telemetry


@dataclass
class ProviderCapabilities:
    """Provider capability detection results."""
    seed_supported: bool = False
    timeout_supported: bool = True  # Most providers honor timeout
    model_hash: Optional[str] = None
    detected_at: Optional[str] = None


class LLMService:
    """
    LLM adapter layer supporting OpenAI-compatible models.
    Follows spec requirement for single adapter supporting model switching via config.
    """

    # Few-shot examples for better LLM code fixing
    FEW_SHOT_EXAMPLES = """
## Example 1: Missing using statement fix
BEFORE (error CS0246: The type or namespace name 'Archive' could not be found):
```csharp
var archive = new Archive("input.zip");
archive.Save("output.zip");
```

AFTER:
```csharp
using Aspose.Zip;

var archive = new Archive("input.zip");
archive.Save("output.zip");
```

## Example 2: Missing wrapper fix
BEFORE (error CS8803: Top-level statements must precede namespace and type declarations):
```csharp
using Aspose.Zip;
class MyClass { }
var archive = new Archive("input.zip");
```

AFTER:
```csharp
using Aspose.Zip;

public class Program
{
    public static void Main(string[] args)
    {
        var archive = new Archive("input.zip");
        archive.Save("output.zip");
    }
}
```

## Example 3: Missing compression settings namespace
BEFORE (error CS0246: The type or namespace name 'DeflateCompressionSettings' could not be found):
```csharp
using Aspose.Zip;

var settings = new DeflateCompressionSettings();
var archive = new Archive(settings);
```

AFTER:
```csharp
using Aspose.Zip;
using Aspose.Zip.Saving;

var settings = new ArchiveEntrySettings(new DeflateCompressionSettings());
using (var archive = new Archive(settings))
{
    archive.CreateEntry("file.txt", "source.txt");
    archive.Save("output.zip");
}
```
"""

    # Error-specific fix instructions
    ERROR_FIX_INSTRUCTIONS = {
        "missing_type": "Add the appropriate 'using' statement at the top. Look up the correct namespace for the missing type in the API catalog context below.",
        "undefined_variable": "Declare the variable before use with proper type, or check if it's a typo",
        "missing_semicolon": "Add semicolon at the end of the statement",
        "missing_brace": "Add the missing closing brace }",
        "type_mismatch": "Use explicit casting or the correct type",
        "member_not_found": "Check the API documentation - the member may not exist or requires different syntax",
        "top_level_statements_error": "Wrap all code in 'class Program { static void Main() { ... } }' structure",
    }

    def __init__(
        self,
        provider: str = "company",
        model: str = "gpt-oss-120b",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3,
        retry_backoff_seconds: int = 5,
        timeout_seconds: int = 120,
        seed: Optional[int] = None,
        deterministic_mode: bool = False,
        enforce_timeout: bool = True,
    ):
        """
        Initialize LLM service.

        Args:
            provider: Provider name ('openai', 'anthropic', 'ollama', etc.)
            model: Model name
            api_key: API key (if None, reads from env)
            base_url: Base URL for API (for self-hosted or proxies)
            temperature: Generation temperature
            max_retries: Maximum retry attempts
            retry_backoff_seconds: Backoff between retries
            timeout_seconds: Request timeout in seconds
            seed: Random seed for deterministic mode
            deterministic_mode: Enable deterministic mode (use seed)
            enforce_timeout: Enforce application-level timeout
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.timeout_seconds = timeout_seconds
        self.seed = seed
        self.deterministic_mode = deterministic_mode
        self.enforce_timeout = enforce_timeout

        # Resolve API key from environment if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url

        # Initialize client
        self._client = None
        self._capabilities: Optional[ProviderCapabilities] = None
        self._capabilities_detected = False
        self._executor = ThreadPoolExecutor(max_workers=2)  # 2 workers to survive starvation from timed-out thread
        self._last_response: Optional[LLMResponse] = None  # Last LLM response for telemetry capture

        # Initialize complexity classifier for smart routing
        self.complexity_classifier = ErrorComplexityClassifier()

        # Initialize routing configuration (will be set by config loader)
        self.routing_config: Optional[Dict[str, Any]] = None
        self.routing_enabled = False
        self._fallback_client = None
        self._ollama_manager = None  # Lazy-initialized OllamaManager for auto-start
        self._circuit_breaker: Optional['CircuitBreaker'] = None  # Passive health monitor

        # Telemetry tracking for routing decisions
        self._tier_distribution = {"small": 0, "medium": 0, "large": 0}
        self._routed_models = {}  # Track which tier used which model

        self._init_client()
    
    def _init_client(self):
        """Initialize the API client with client-level timeout."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available. LLM features disabled.")
            return

        # Diagnostic logging for provider routing
        api_key_status = f"SET ({len(self.api_key)} chars)" if self.api_key else "MISSING"
        logger.info(
            f"LLM client init: provider={self.provider}, model={self.model}, "
            f"base_url={self.base_url}, api_key={api_key_status}"
        )

        # Guard against OPENAI_BASE_URL env var silently overriding code-level base_url
        env_base_url = os.getenv("OPENAI_BASE_URL")
        if env_base_url and self.base_url and env_base_url != self.base_url:
            logger.warning(
                f"OPENAI_BASE_URL env var ({env_base_url}) differs from configured "
                f"base_url ({self.base_url}). Removing env var to prevent silent override."
            )
            os.environ.pop("OPENAI_BASE_URL", None)

        client_kwargs = {}

        # Add client-level timeout (C.5: client timeout)
        if self.enforce_timeout:
            client_kwargs["timeout"] = self.timeout_seconds

        if self.provider == "ollama":
            # Ollama doesn't require a real API key
            client_kwargs["base_url"] = self.base_url or "http://localhost:11434/v1"
            client_kwargs["api_key"] = "ollama"  # Ollama requires a placeholder
        else:
            # All other providers use OpenAI-compatible API (openai, azure, company, etc.)
            if not self.api_key:
                logger.warning(f"No API key provided for {self.provider}. LLM features disabled.")
                return
            client_kwargs["api_key"] = self.api_key
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

        try:
            self._client = OpenAI(**client_kwargs)
            # Verify the client's actual base_url matches what we intended
            actual_base = str(self._client.base_url).rstrip("/")
            intended_base = (client_kwargs.get("base_url") or "https://api.openai.com/v1").rstrip("/")
            if actual_base != intended_base:
                logger.warning(
                    f"Client base_url mismatch! Intended: {intended_base}, "
                    f"Actual: {actual_base}. Check OPENAI_BASE_URL env var."
                )
            logger.info(
                f"LLM client initialized: provider={self.provider}, "
                f"base_url={actual_base}, timeout={self.timeout_seconds}s"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}. LLM features disabled.")
            self._client = None
    
    def is_available(self) -> bool:
        """Check if LLM service is available and properly configured."""
        if self._client is None:
            return False
        # For non-Ollama providers, require API key
        if self.provider != "ollama" and not self.api_key:
            return False
        return True

    def preflight_check(self) -> Dict[str, Any]:
        """
        Perform a lightweight availability check on primary and fallback endpoints.
        Returns a dict with status of each endpoint.
        """
        result = {
            "primary": {"available": False, "model": self.model, "base_url": self.base_url, "error": None},
            "fallback": {"available": False, "model": None, "base_url": None, "error": None},
        }

        # Check primary
        if self._client:
            try:
                self._client.models.list()
                result["primary"]["available"] = True
            except Exception as e:
                result["primary"]["error"] = str(e)[:200]
        else:
            result["primary"]["error"] = "Client not initialized (missing API key?)"

        # Check fallback
        if self.routing_config and self.routing_config.get("fallback_enabled", True):
            fallback_client = self._get_fallback_client()
            fallback_model = self._get_fallback_model()
            result["fallback"]["model"] = fallback_model

            providers = self.routing_config.get("providers", {})
            ollama_config = providers.get("ollama", {})
            result["fallback"]["base_url"] = ollama_config.get("base_url", "http://localhost:11434/v1")

            if fallback_client:
                try:
                    fallback_client.models.list()
                    result["fallback"]["available"] = True
                except Exception as e:
                    result["fallback"]["error"] = str(e)[:200]
                    # Auto-start Ollama if configured
                    if ollama_config.get("auto_start", True):
                        ollama_status = self._ensure_ollama_running(ollama_config)
                        if ollama_status and ollama_status.is_running:
                            self._fallback_client = None  # Force re-creation
                            fallback_client = self._get_fallback_client()
                            if fallback_client:
                                try:
                                    fallback_client.models.list()
                                    result["fallback"]["available"] = True
                                    result["fallback"]["error"] = None
                                    result["fallback"]["auto_started"] = True
                                except Exception as e2:
                                    result["fallback"]["error"] = f"Auto-started but still unavailable: {str(e2)[:150]}"
            else:
                result["fallback"]["error"] = "Fallback client not initialized"
                # Also try auto-start if client wasn't initialized
                if ollama_config.get("auto_start", True):
                    ollama_status = self._ensure_ollama_running(ollama_config)
                    if ollama_status and ollama_status.is_running:
                        self._fallback_client = None
                        fallback_client = self._get_fallback_client()
                        if fallback_client:
                            try:
                                fallback_client.models.list()
                                result["fallback"]["available"] = True
                                result["fallback"]["error"] = None
                                result["fallback"]["auto_started"] = True
                            except Exception:
                                pass

        # Expose circuit breaker state for logging / dashboard
        if self._circuit_breaker:
            result["circuit_breaker"] = self._circuit_breaker.get_status()

        return result

    def set_routing_config(self, routing_config: Dict[str, Any]) -> None:
        """
        Set model routing configuration.

        Args:
            routing_config: Configuration dict with model_tiers, providers, circuit_breaker, etc.
        """
        self.routing_config = routing_config
        self.routing_enabled = routing_config.get("enabled", False)

        # Build circuit breaker if fallback (Ollama) is configured
        if CIRCUIT_BREAKER_AVAILABLE:
            has_fallback = bool(routing_config.get("providers", {}).get("ollama"))
            cb_cfg = routing_config.get("circuit_breaker", {})
            # Handle both dict (from JSON) and Pydantic model (from model_dump)
            if hasattr(cb_cfg, "model_dump"):
                cb_cfg = cb_cfg.model_dump()
            self._circuit_breaker = build_circuit_breaker_from_config(cb_cfg, has_fallback)

        logger.info(
            "Model routing %s, circuit_breaker=%s",
            "enabled" if self.routing_enabled else "disabled",
            "active" if self._circuit_breaker else "disabled",
        )

    def _get_fallback_client(self) -> Optional[OpenAI]:
        """
        Get or create a fallback client (Ollama).

        Returns:
            OpenAI client for Ollama, or None if initialization fails
        """
        if self._fallback_client is not None:
            return self._fallback_client

        if not self.routing_config:
            logger.warning("No routing config available for fallback client")
            return None

        try:
            providers = self.routing_config.get("providers", {})
            ollama_config = providers.get("ollama", {})

            if not ollama_config:
                logger.warning("Ollama configuration not found in routing config")
                return None

            base_url = ollama_config.get("base_url", "http://localhost:11434/v1")
            timeout = ollama_config.get("timeout_seconds", 120)

            client_kwargs = {
                "base_url": base_url,
                "api_key": "ollama",
                "timeout": timeout if self.enforce_timeout else None,
            }

            self._fallback_client = OpenAI(**client_kwargs)
            logger.debug(f"Initialized fallback Ollama client at {base_url}")
            return self._fallback_client

        except Exception as e:
            logger.error(f"Failed to initialize fallback Ollama client: {e}")
            return None

    def _get_fallback_model(self) -> str:
        """Get the model name for the fallback provider."""
        if self.routing_config:
            providers = self.routing_config.get("providers", {})
            ollama_config = providers.get("ollama", {})
            return ollama_config.get("model", "qwen2.5-coder:7b")
        return "qwen2.5-coder:7b"

    def _ensure_ollama_running(self, ollama_config: Dict[str, Any]):
        """
        Ensure Ollama is running, using OllamaManager for lifecycle management.

        Args:
            ollama_config: Ollama provider configuration dict

        Returns:
            OllamaStatus if manager was created, None if unavailable
        """
        if self._ollama_manager is not None:
            return self._ollama_manager.ensure_running()

        try:
            from .ollama_manager import OllamaManager

            # Strip /v1 suffix — OllamaManager uses the native API (not OpenAI-compat)
            base_url = ollama_config.get("base_url", "http://localhost:11434/v1")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]

            self._ollama_manager = OllamaManager(
                base_url=base_url,
                model=ollama_config.get("model", "qwen2.5-coder:7b"),
                auto_start=ollama_config.get("auto_start", True),
                startup_timeout_seconds=ollama_config.get("startup_timeout_seconds", 30),
                auto_pull_model=ollama_config.get("auto_pull_model", True),
                pull_timeout_seconds=ollama_config.get("pull_timeout_seconds", 600),
            )

            return self._ollama_manager.ensure_running()

        except ImportError:
            logger.warning("OllamaManager not available")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize OllamaManager: {e}")
            return None

    def _try_ollama_fallback(
        self, model: str, messages: List[Dict], reason: str = "unknown", **kwargs
    ) -> Optional[Any]:
        """
        Attempt the Ollama fallback endpoint, auto-starting Ollama if needed.

        Args:
            model: Original model name (for logging; Ollama uses its own model)
            messages: Chat messages to send
            reason: Why fallback is being used (for log context)
            **kwargs: Additional arguments for chat.completions.create

        Returns:
            Response object from Ollama, or None if fallback also fails
        """
        if not self.routing_config:
            return None
        providers = self.routing_config.get("providers", {})
        ollama_config = providers.get("ollama", {})
        if ollama_config.get("auto_start", True):
            self._ensure_ollama_running(ollama_config)
        fallback_client = self._get_fallback_client()
        if fallback_client:
            fallback_model = self._get_fallback_model()
            logger.info(
                "llm_fallback_to_ollama reason=%s primary_model=%s fallback_model=%s",
                reason, model, fallback_model,
            )
            try:
                return fallback_client.chat.completions.create(
                    model=fallback_model, messages=messages, **kwargs
                )
            except Exception as fallback_e:
                logger.error("ollama_fallback_failed reason=%s error=%s", reason, fallback_e)
        return None

    def _call_with_fallback(self, model: str, messages: List[Dict], **kwargs) -> Optional[Any]:
        """
        Call primary LLM (professionalize.LLM) with circuit-breaker-aware fallback to Ollama.

        Flow:
          1. If circuit breaker is OPEN → route directly to Ollama (proactive routing)
          2. Otherwise try primary; record success/failure with latency for circuit breaker
          3. On primary failure → attempt Ollama (reactive fallback, existing behavior)

        Args:
            model: Model name to use on primary
            messages: Chat messages
            **kwargs: Additional arguments for chat.completions.create

        Returns:
            Response object, or None if both primary and fallback fail
        """
        if not self.routing_config or not self.routing_config.get("fallback_enabled", True):
            # Routing disabled — use primary client directly
            if self._client:
                return self._client.chat.completions.create(model=model, messages=messages, **kwargs)
            return None

        # ── Proactive routing: skip primary when circuit breaker is OPEN ──
        if self._circuit_breaker and self._circuit_breaker.should_use_fallback():
            cb_status = self._circuit_breaker.get_status()
            logger.info(
                "circuit_breaker_proactive_route state=%s consecutive_failures=%d "
                "error_rate=%.2f avg_latency_s=%.1f",
                cb_status["state"],
                cb_status["consecutive_failures"],
                cb_status["error_rate"],
                cb_status["avg_latency_s"],
            )
            return self._try_ollama_fallback(model, messages, reason="circuit_open", **kwargs)

        # ── Primary call with latency tracking ──
        if not self._client:
            logger.warning("primary_client_unavailable routing_to_ollama")
            return self._try_ollama_fallback(model, messages, reason="no_primary_client", **kwargs)

        _t0 = time.time()
        try:
            logger.debug("calling_primary_provider model=%s", model)
            response = self._client.chat.completions.create(model=model, messages=messages, **kwargs)
            _latency_s = time.time() - _t0
            if self._circuit_breaker:
                self._circuit_breaker.record_success(_latency_s)
            return response

        except Exception as e:
            _latency_s = time.time() - _t0
            # Record transient failures for circuit breaker (skip auth/permanent errors)
            if self._circuit_breaker and _is_transient_error(e):
                self._circuit_breaker.record_failure(_latency_s)
                cb_status = self._circuit_breaker.get_status()
                logger.info(
                    "circuit_breaker_failure_recorded state=%s consecutive_failures=%d",
                    cb_status["state"],
                    cb_status["consecutive_failures"],
                )

            if self.routing_config.get("fallback_on_error", True):
                logger.warning(
                    "primary_provider_failed error_type=%s error=%s falling_back_to_ollama",
                    type(e).__name__, e,
                )
                return self._try_ollama_fallback(
                    model, messages, reason=type(e).__name__, **kwargs
                )
            raise

    def get_provider_capabilities(self) -> ProviderCapabilities:
        """
        Get provider capabilities (seed support, timeout support).
        Performs capability detection on first call.

        Returns:
            ProviderCapabilities with detected features
        """
        if self._capabilities_detected:
            return self._capabilities

        # Perform capability detection
        self._capabilities = self._detect_capabilities()
        self._capabilities_detected = True

        return self._capabilities

    def _detect_capabilities(self) -> ProviderCapabilities:
        """
        Detect provider capabilities (seed, timeout, model hash).

        Returns:
            ProviderCapabilities with detection results
        """
        capabilities = ProviderCapabilities()
        capabilities.detected_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not self._client:
            logger.warning("Cannot detect capabilities: client not initialized")
            return capabilities

        # Test seed support with a minimal request
        # We assume seed is supported by default and check if it's accepted
        try:
            test_messages = [{"role": "user", "content": "Say 'test' only."}]
            test_kwargs = {
                "model": self.model,
                "messages": test_messages,
                "max_tokens": 10,
                "temperature": 0.0,
            }

            # Try with seed
            if self.seed is not None:
                test_kwargs["seed"] = self.seed

            # Use a short timeout for capability detection
            if self.enforce_timeout:
                test_kwargs["timeout"] = min(10, self.timeout_seconds)

            response = self._client.chat.completions.create(**test_kwargs)

            # If we get here without exception, seed is likely supported
            capabilities.seed_supported = True
            capabilities.timeout_supported = True

            # Try to extract model hash if available (provider-specific)
            if hasattr(response, 'system_fingerprint'):
                capabilities.model_hash = response.system_fingerprint

            logger.info(
                f"Capability detection complete: seed_supported={capabilities.seed_supported}, "
                f"timeout_supported={capabilities.timeout_supported}"
            )

        except Exception as e:
            # If seed caused an error, mark as unsupported
            error_str = str(e).lower()
            if 'seed' in error_str or 'not supported' in error_str:
                capabilities.seed_supported = False
                logger.warning(f"Provider {self.provider} does not support seed parameter: {e}")
            else:
                # Assume seed is supported, other error
                capabilities.seed_supported = True
                logger.debug(f"Capability detection encountered error (assuming seed supported): {e}")

        return capabilities
    
    def _call_with_timeout(self, func, timeout_seconds: int, label: str) -> Any:
        """
        Execute a blocking function with application-level timeout.

        Args:
            func: Callable to execute
            timeout_seconds: Timeout in seconds
            label: Label for error messages

        Returns:
            Function result

        Raises:
            TimeoutError: If timeout is exceeded
        """
        future = self._executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeout:
            future.cancel()  # Best-effort cancellation of stuck thread
            logger.error(
                f"LLM timeout exceeded after {timeout_seconds}s: {label} "
                f"(provider={self.provider}, model={self.model})"
            )
            raise TimeoutError(
                f"LLM request timeout after {timeout_seconds}s: {label} "
                f"(provider={self.provider}, model={self.model})"
            )

    def _extract_error_code_from_logs(self, error_logs: str) -> Optional[str]:
        """
        Extract first error code from error logs.

        Looks for patterns like CS0246, CS0103, etc.

        Args:
            error_logs: Error log text

        Returns:
            Error code (e.g., 'CS0246') or None if not found
        """
        # Match C# error codes (CS followed by 4 digits)
        match = re.search(r'\b(CS\d{4})\b', error_logs)
        if match:
            return match.group(1)
        return None

    def _select_model_for_error(
        self,
        error_code: str,
        error_message: str,
        retry_count: int = 0,
        all_errors: Optional[List[str]] = None,
    ) -> str:
        """
        Select model tier based on error complexity.

        Args:
            error_code: Error code (e.g., 'CS0246')
            error_message: Full error message
            retry_count: Number of previous attempts
            all_errors: List of error codes in current compile attempt

        Returns:
            Model name to use for this error
        """
        if not self.routing_enabled or not self.routing_config:
            # Routing disabled, return default model
            return self.model

        try:
            # Score the error complexity
            context = {
                "retry_count": retry_count,
                "all_errors": all_errors or [],
                "error_history": [],  # Could be populated from context
            }

            score = self.complexity_classifier.score_error(error_code, error_message, context)
            tier = self.complexity_classifier.route_to_tier(score)

            # Track tier distribution for telemetry
            self._tier_distribution[tier] = self._tier_distribution.get(tier, 0) + 1

            # Get model for this tier
            model_tiers = self.routing_config.get("model_tiers", {})
            model = model_tiers.get(tier, self.model)

            # Track which model was routed to this tier
            self._routed_models[tier] = model

            logger.info(
                f"Routed error {error_code} to {tier} tier (score={score:.2f}), "
                f"using model: {model}"
            )

            return model

        except Exception as e:
            logger.error(f"Error in model selection: {e}. Using default model.")
            return self.model

    def get_tier_distribution(self) -> Dict[str, int]:
        """
        Get the distribution of errors routed to each tier.

        Returns:
            Dictionary with tier counts
        """
        return self._tier_distribution.copy()

    def get_routing_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about routing decisions.

        Returns:
            Dictionary with routing stats
        """
        return {
            "routing_enabled": self.routing_enabled,
            "tier_distribution": self.get_tier_distribution(),
            "routed_models": self._routed_models.copy(),
        }

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        timeout_override: Optional[int] = None,
        error_logs: Optional[str] = None,
        routing_context: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Override default temperature
            stop: Stop sequences
            timeout_override: Override configured timeout
            error_logs: Error logs for complexity-based routing (optional)
            routing_context: Additional routing context with retry_count, all_errors (optional)

        Returns:
            LLMResponse with content and metadata
        """
        if not self._client:
            # Primary client unavailable — attempt fallback if routing is configured
            if self.routing_config and self.routing_config.get("fallback_enabled", True):
                fallback_client = self._get_fallback_client()
                if fallback_client:
                    fallback_model = self._get_fallback_model()
                    logger.warning(
                        f"Primary client not initialized, using fallback: {fallback_model}"
                    )
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})
                    try:
                        import time as _time
                        start = _time.time()
                        response = fallback_client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature if temperature is not None else self.temperature,
                        )
                        elapsed = int((_time.time() - start) * 1000)
                        content = response.choices[0].message.content if response.choices else ""
                        return LLMResponse(
                            content=content,
                            model=fallback_model,
                            usage=dict(response.usage) if response.usage else {},
                            finish_reason=response.choices[0].finish_reason if response.choices else "error",
                            latency_ms=elapsed,
                            success=True,
                            error=None,
                        )
                    except Exception as e:
                        logger.error(f"Fallback client also failed in complete(): {e}")

            return LLMResponse(
                content="",
                model=self.model,
                usage={},
                finish_reason="error",
                latency_ms=0,
                success=False,
                error="LLM client not initialized (primary and fallback both unavailable)"
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        temp = temperature if temperature is not None else self.temperature
        timeout = timeout_override if timeout_override is not None else self.timeout_seconds

        # Select model based on error complexity if routing is enabled
        selected_model = self.model
        if self.routing_enabled and error_logs:
            error_code = self._extract_error_code_from_logs(error_logs)
            if error_code:
                ctx = routing_context or {}
                selected_model = self._select_model_for_error(
                    error_code,
                    error_logs,
                    retry_count=ctx.get("retry_count", 0),
                    all_errors=ctx.get("all_errors", []),
                )
                logger.debug(f"Selected model {selected_model} for error {error_code}")

        # Get capabilities on first call (lazy detection)
        if not self._capabilities_detected:
            capabilities = self.get_provider_capabilities()
        else:
            capabilities = self._capabilities

        last_error = None
        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                # Build request kwargs
                # For routing path, model/messages passed explicitly; for direct path, in kwargs
                request_kwargs = {
                    "model": selected_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temp,
                }

                if stop:
                    request_kwargs["stop"] = stop

                # Add seed if deterministic mode is enabled and seed is configured
                if self.deterministic_mode and self.seed is not None:
                    if capabilities and capabilities.seed_supported:
                        request_kwargs["seed"] = self.seed
                    else:
                        logger.warning(
                            f"Deterministic mode enabled but provider {self.provider} "
                            f"does not support seed parameter"
                        )

                # Application-level timeout enforcement (C.5: wall timeout)
                def make_request():
                    if self.routing_enabled and self.routing_config:
                        # Use fallback chain
                        # Extract model and messages from request_kwargs for explicit passing
                        fallback_kwargs = {k: v for k, v in request_kwargs.items()
                                         if k not in ("model", "messages")}
                        return self._call_with_fallback(selected_model, messages, **fallback_kwargs)
                    else:
                        # Use primary client
                        return self._client.chat.completions.create(**request_kwargs)

                if self.enforce_timeout:
                    response = self._call_with_timeout(
                        make_request,
                        timeout,
                        f"LLM complete (attempt {attempt + 1}, model={selected_model})"
                    )
                else:
                    response = make_request()

                latency_ms = int((time.time() - start_time) * 1000)

                choice = response.choices[0]
                resp = LLMResponse(
                    content=choice.message.content or "",
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                    finish_reason=choice.finish_reason or "stop",
                    latency_ms=latency_ms,
                    success=True,
                    raw_prompt=prompt,
                )
                self._last_response = resp
                return resp

            except TimeoutError as e:
                last_error = str(e)
                logger.error(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                # Don't retry on timeout - fail fast
                break

            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))

        err_resp = LLMResponse(
            content="",
            model=selected_model,
            usage={},
            finish_reason="error",
            latency_ms=0,
            success=False,
            error=last_error or "Unknown error",
            raw_prompt=prompt,
        )
        self._last_response = err_resp
        return err_resp
    
    def fix_code(
        self,
        code: str,
        error_logs: str,
        context_type: str = "compile",
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
        test_data_info: Optional[str] = None,
        family_config: Optional[Dict[str, Any]] = None,
        scaffolding_hints: Optional[List[str]] = None,
        section_heading: Optional[str] = None,
        description_context: Optional[str] = None,
        topic: Optional[str] = None,
        original_code: Optional[str] = None,
        catalog=None,
    ) -> LLMResponse:
        """
        Fix code using LLM with enhanced context.

        Args:
            code: Original code with errors
            error_logs: Compiler/runtime error output
            context_type: 'compile' or 'runtime'
            api_context: Relevant API documentation
            similar_examples: Similar working examples from vector DB
            test_data_info: Information about available test data files
            family_config: Family configuration dictionary (for API patterns)
            scaffolding_hints: Specific hints for fixing (from error categorization)
            section_heading: Markdown heading above the code block
            description_context: Paragraphs before the code block
            topic: Topic inferred from file path
            original_code: Original code before any fixes (for anchoring)
            catalog: APICatalogService instance for enriched error context (optional)

        Returns:
            LLMResponse with fixed code
        """
        if context_type == "runtime":
            return self._fix_runtime_code(
                code, error_logs, api_context, similar_examples, test_data_info,
                family_config, scaffolding_hints, section_heading, description_context, topic,
                original_code, catalog=catalog,
            )
        else:
            return self._fix_compile_code(
                code, error_logs, api_context, similar_examples, family_config,
                scaffolding_hints, section_heading, description_context, topic,
                original_code, catalog=catalog,
            )
    
    def _get_api_patterns(self, family_config: Optional[Dict[str, Any]]) -> str:
        """
        Extract API patterns from family configuration.

        Args:
            family_config: Family configuration dictionary

        Returns:
            Formatted API patterns string
        """
        if not family_config or 'api_patterns' not in family_config:
            return ""

        patterns = []
        api_patterns = family_config.get('api_patterns', {})

        for pattern_name, pattern_info in api_patterns.items():
            description = pattern_info.get('description', '')
            code = pattern_info.get('code', '')
            if code:
                patterns.append(f"### {pattern_name.replace('_', ' ').title()}")
                if description:
                    patterns.append(f"// {description}")
                patterns.append("```csharp")
                patterns.append(code)
                patterns.append("```")

        return "\n".join(patterns) if patterns else ""

    def _get_api_context_for_error(
        self,
        error_code: str,
        error_message: str,
    ) -> str:
        """
        Extract API context for an error.

        Note: APIContextService has been removed (TASK-DLL-03).
        This method is kept as a stub to avoid breaking callers; it always returns "".

        Args:
            error_code: Error code (e.g., 'CS0103')
            error_message: Full error message

        Returns:
            Empty string (service removed)
        """
        return ""

    def _build_catalog_context(self, error_code: str, error_message: str, catalog) -> str:
        """
        Build targeted catalog context for a specific error.

        Uses the APICatalogService to provide precise API reference data
        (namespace, enum members, constructor signatures) relevant to the
        specific error being fixed.  Keeps output to 100-300 tokens max.

        Args:
            error_code: C# error code (e.g. 'CS0246', 'CS0103')
            error_message: Full error message text
            catalog: APICatalogService instance

        Returns:
            Formatted context string, or empty string if no relevant context.
        """
        if catalog is None or not catalog.is_loaded:
            return ""

        parts: List[str] = []

        # ---- Extract type/symbol names from error message ----
        # CS0246: "The type or namespace name 'Foo' could not be found"
        # CS0103: "The name 'Foo' does not exist in the current context"
        # CS0234: "The type or namespace name 'Foo' does not exist in 'Bar'"
        type_names: List[str] = []
        if error_code in ("CS0246", "CS0103", "CS0234"):
            matches = re.findall(r"'(\w+)'", error_message)
            type_names = matches[:3]  # Limit to first 3 extracted names

        # CS1503: "cannot convert from 'X' to 'Y'"
        elif error_code == "CS1503":
            matches = re.findall(r"'(\w+)'", error_message)
            type_names = matches[:4]

        # CS7036: "no argument given that corresponds to required parameter 'x' of 'Type.Method'"
        elif error_code == "CS7036":
            matches = re.findall(r"'(\w[\w.]*)'", error_message)
            type_names = matches[:3]

        # CS0117: "'Type' does not contain a definition for 'Member'"
        elif error_code == "CS0117":
            matches = re.findall(r"'(\w+)'", error_message)
            type_names = matches[:2]

        # CS1061: "'Type' does not contain a definition for 'Member'"
        elif error_code == "CS1061":
            matches = re.findall(r"'([\w.]+)'", error_message)
            type_names = [m.split(".")[-1] for m in matches[:2]]

        # CS0104: "ambiguous reference between 'NS1.Type' and 'NS2.Type'"
        elif error_code == "CS0104":
            matches = re.findall(r"'([\w.]+)'", error_message)
            # Extract simple type name from qualified names
            for m in matches[:2]:
                simple = m.rsplit(".", 1)[-1]
                if simple not in type_names:
                    type_names.append(simple)

        # Generic fallback: try to extract quoted identifiers
        if not type_names:
            matches = re.findall(r"'(\w+)'", error_message)
            type_names = [m for m in matches[:2] if len(m) > 1]

        # ---- Look up each extracted name in the catalog ----
        namespaces_mentioned: set = set()
        for name in type_names:
            ns = catalog.get_namespace_for_type(name)
            if ns:
                using = catalog.get_using_directive(name)
                parts.append(f"- `{name}` is in namespace `{ns}`")
                if using:
                    parts.append(f"  Add: `{using}`")
                namespaces_mentioned.add(ns)

                # For CS0117/CS0103: show enum members if it's an enum
                if error_code in ("CS0117", "CS0103"):
                    members = catalog.get_enum_members(name)
                    if members:
                        display = ", ".join(members[:10])
                        if len(members) > 10:
                            display += f", ... ({len(members)} total)"
                        parts.append(f"  Enum members: {display}")

                # For CS1061: show properties and methods (member not found)
                if error_code == "CS1061":
                    all_members = catalog.get_all_members(name)
                    if all_members:
                        display = ", ".join(all_members[:15])
                        if len(all_members) > 15:
                            display += f", ... ({len(all_members)} total)"
                        parts.append(f"  Known members: {display}")

                # For CS7036/CS1503: show constructor signatures
                if error_code in ("CS7036", "CS1503"):
                    ctors = catalog.get_constructor_signatures(name)
                    if ctors:
                        parts.append(f"  Constructor overloads for `{name}`:")
                        for ctor in ctors[:5]:
                            params = ctor.get("params", "")
                            parts.append(f"    new {name}({params})")

            # Check ambiguity for CS0104
            if error_code == "CS0104" and catalog.is_ambiguous(name):
                amb_ns = catalog.get_ambiguous_namespaces(name)
                parts.append(f"- `{name}` is ambiguous across: {', '.join(amb_ns)}")
                parts.append(f"  Use fully qualified name (e.g. `{amb_ns[0]}.{name}`)")

        # ---- Add mined using patterns if available ----
        if hasattr(catalog, 'mine_using_patterns') and type_names:
            try:
                mined_patterns = catalog.mine_using_patterns(self.family, self.db)
                for name in type_names:
                    if name in mined_patterns and mined_patterns[name]:
                        parts.append(f"- Reference examples using `{name}` typically include:")
                        for using in mined_patterns[name][:5]:  # Limit to 5 usings
                            parts.append(f"    using {using};")
            except Exception as e:
                # Graceful degradation - log but don't fail
                logger.debug(f"Could not mine using patterns: {e}")

        # ---- Add namespace list summary (for CS0246/CS0234 missing using) ----
        if error_code in ("CS0246", "CS0234") and not parts:
            # Type not found in catalog, provide namespace list for reference
            all_ns = sorted(catalog.get_namespace_set())
            if all_ns:
                parts.append(f"Available namespaces ({len(all_ns)}):")
                # Show up to 15 namespaces
                for ns in all_ns[:15]:
                    parts.append(f"  - {ns}")
                if len(all_ns) > 15:
                    parts.append(f"  ... and {len(all_ns) - 15} more")

        return "\n".join(parts) if parts else ""

    def _build_few_shot_section(
        self,
        error_logs: str,
        family: str,
        catalog=None,
        similar_examples=None
    ) -> str:
        """Build family-specific few-shot examples from reference corpus.

        Falls back to static FEW_SHOT_EXAMPLES when no dynamic examples available.

        Args:
            error_logs: Compilation error output
            family: Family name (zip, words, etc.)
            catalog: Optional API catalog for error-specific context
            similar_examples: Optional list that can be either:
                             - List of code strings (current orchestrator format)
                             - List of (example_id, code, score, metadata) tuples (future)

        Returns:
            Formatted few-shot examples section for LLM prompt
        """
        parts = ["## Minimal Fix Patterns:"]

        # Extract error code for optional enhancement
        error_code = None
        error_code_match = re.search(r'(CS\d{4})', error_logs)
        if error_code_match:
            error_code = error_code_match.group(1)

        # Use similar CS_FILE examples if available (tuple format only)
        if similar_examples:
            # Check if we have tuple format (enhanced) or string format (current)
            if similar_examples and isinstance(similar_examples[0], tuple):
                cs_file_count = 0
                for item in similar_examples[:2]:
                    # Unpack tuple: (example_id, code, score, metadata)
                    ex_id, code, score, meta = item
                    # Prioritize CS_FILE (canonical reference) examples
                    if meta.get("source_type") == "cs_file":
                        topic = meta.get("topic", "similar example")
                        parts.append(f"\nWorking reference example ({topic}):")
                        parts.append("```csharp")
                        # Limit to first 500 chars to keep prompt concise
                        parts.append(code[:500])
                        if len(code) > 500:
                            parts.append("// ... (truncated)")
                        parts.append("```")
                        cs_file_count += 1

                # If we found CS_FILE examples, use them instead of static examples
                if cs_file_count > 0:
                    if error_code:
                        parts.append(f"\n(Error-specific patterns for {error_code})")
                    return "\n".join(parts)

        # Fallback to static examples when vector DB disabled, string format, or no CS_FILE matches
        parts.append(self.FEW_SHOT_EXAMPLES)
        return "\n".join(parts)

    def _fix_compile_code(
        self,
        code: str,
        error_logs: str,
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
        family_config: Optional[Dict[str, Any]] = None,
        scaffolding_hints: Optional[List[str]] = None,
        section_heading: Optional[str] = None,
        description_context: Optional[str] = None,
        topic: Optional[str] = None,
        original_code: Optional[str] = None,
        catalog=None,
    ) -> LLMResponse:
        """Fix compilation errors with enhanced context and minimal-change rules."""

        # Build topic context for minimal-change guidance
        topic_context = topic or "demonstrating the API usage"

        system_prompt = f"""You are an expert C# developer fixing code examples in documentation.

CRITICAL RULES - FOLLOW EXACTLY:
1. Make MINIMAL changes - only fix the specific error, nothing more
2. Do NOT add new functionality, imports, or code beyond what's absolutely needed
3. Do NOT refactor, improve, optimize, or expand the code
4. Keep the code focused on its ORIGINAL PURPOSE: {topic_context}
5. The code must remain relevant to the documentation context
6. Return ONLY valid C# code - no explanations, no markdown formatting

ALLOWED FIXES (in order of preference):
- Add missing 'using' statements for types that can't be found
- Fix syntax errors (missing semicolons, braces)
- Wrap in class/Main ONLY if required for standalone execution
- Fix obvious type mismatches

DO NOT:
- Add error handling unless it was already there
- Add null checks unless the error specifically requires it
- Change variable names
- Add comments or documentation
- Restructure the code logic
- Add features or functionality

If you cannot fix the code without major changes, return the original code unchanged."""

        prompt_parts = [
            "Fix the following C# code that has compilation errors.",
        ]

        # Add content context prominently at the top
        if section_heading or description_context:
            prompt_parts.extend([
                "",
                "## DOCUMENTATION CONTEXT (the code must remain relevant to this):",
            ])
            if section_heading:
                prompt_parts.append(f"Section: {section_heading}")
            if description_context:
                prompt_parts.append(f"Description: {description_context[:500]}")

        # Add original code section if provided and different from current code
        if original_code and original_code.strip() != code.strip():
            prompt_parts.extend([
                "",
                "## Original Code (teaching intent reference):",
                "```csharp",
                original_code,
                "```",
                "",
                "**CRITICAL**: The original code demonstrates a specific concept/feature.",
                "Your fix MUST preserve this teaching intent.",
                "Do NOT add features, error handling, or complexity beyond what's needed to make it compile/run.",
            ])

        prompt_parts.extend([
            "",
            "## Current Code (to be fixed):",
            "```csharp",
            code,
            "```",
            "",
            "## Compilation Errors:",
            "```",
            error_logs,
            "```",
        ])

        # Add Fix Instructions
        prompt_parts.extend([
            "",
            "## Fix Instructions:",
            "1. **Minimal Changes**: Make ONLY the changes needed to fix the errors",
            "2. **Preserve Intent**: The fixed code must demonstrate the SAME concept as the original",
            "3. **No Scope Creep**: Do NOT add error handling, validation, or features not in the original",
            "4. **Teaching Clarity**: A reader should understand the same lesson from your fix",
        ])

        # Add BAD fixes examples (including semantic drift prevention)
        prompt_parts.extend([
            "",
            "## Examples of BAD fixes (scope creep and semantic drift):",
            "- Adding try-catch blocks when original had none",
            "- Adding File.Exists() checks when original assumed file exists",
            "- Adding complex error messages when original used simple code",
            "- Restructuring code into methods when original was inline",
            "- Changing enum values (e.g., DecodeType.Code39 to DecodeType.DataMatrix)",
            "- Removing property customizations (e.g., deleting BarColor, BackColor assignments)",
            "- Changing constructor types (e.g., BarcodeGenerator to BarCodeReader)",
            "- Switching API modes (e.g., generation to recognition, save to load)",
        ])

        # Add GOOD fixes examples
        prompt_parts.extend([
            "",
            "## Examples of GOOD fixes (minimal):",
            "✅ Adding missing using statement",
            "✅ Fixing typo in variable name",
            "✅ Correcting API method signature",
            "✅ Adding namespace qualification",
        ])

        # Add scaffolding hints if available
        if scaffolding_hints:
            prompt_parts.extend([
                "",
                "## Fix Hints (apply these minimal changes):",
            ])
            for hint in scaffolding_hints:
                prompt_parts.append(f"- {hint}")

        # Add few-shot examples (dynamic or static)
        family_name = family_config.get("family", "unknown") if isinstance(family_config, dict) else (family_config.family if family_config else "unknown")
        few_shot_section = self._build_few_shot_section(
            error_logs, family_name, catalog, similar_examples
        )
        prompt_parts.extend([
            "",
            few_shot_section,
        ])

        # Add API patterns from config
        api_patterns = self._get_api_patterns(family_config)
        if api_patterns:
            prompt_parts.extend([
                "",
                "## API Usage Patterns (use these as reference):",
                api_patterns,
            ])

        # Inject API context from error analysis if not already provided
        injected_api_context = ""
        if not api_context and error_logs:
            injected_api_context = self._get_api_context_for_error(
                self._extract_error_code_from_logs(error_logs) or "UNKNOWN",
                error_logs
            )

        # Use either passed-in context or injected context
        final_api_context = api_context or injected_api_context
        if final_api_context:
            prompt_parts.extend([
                "",
                "## Relevant API Documentation:",
                final_api_context,
            ])

        # Inject targeted catalog context for this specific error (TASK-DLL-07)
        if catalog:
            error_code = self._extract_error_code_from_logs(error_logs) or "UNKNOWN"
            catalog_context = self._build_catalog_context(error_code, error_logs, catalog)
            if catalog_context:
                prompt_parts.extend([
                    "",
                    "## Exact API Reference (from assembly catalog):",
                    catalog_context,
                ])

            # Also inject namespace list for missing-type errors
            if error_code in ("CS0246", "CS0234", "CS0103"):
                all_ns = sorted(catalog.get_namespace_set())
                if all_ns:
                    ns_str = ", ".join(all_ns[:20])
                    if len(all_ns) > 20:
                        ns_str += f", ... ({len(all_ns)} total)"
                    prompt_parts.extend([
                        "",
                        f"## Known Namespaces: {ns_str}",
                    ])

        if similar_examples:
            prompt_parts.extend([
                "",
                "## Similar Working Examples:",
            ])
            for i, example in enumerate(similar_examples[:2], 1):
                prompt_parts.extend([
                    f"### Example {i}:",
                    "```csharp",
                    example,
                    "```",
                ])

        prompt_parts.extend([
            "",
            "Return ONLY the corrected C# code. Make MINIMAL changes - fix only what's broken:",
        ])

        response = self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            max_tokens=4096,
            error_logs=error_logs,  # Pass error logs for complexity-based routing
        )

        # Clean up response - remove markdown code blocks if present
        # Note: Using new validation with format correction retry
        if response.success and response.content:
            original_content = response.content
            cleaned, rejection_reason = self._clean_code_response(
                response.content,
                error_category="compile",
                db=None,  # Not available in this context
                run_id=None,
                family=None,
                example_id=None,
            )
            response.content = cleaned

            # Optional: Attempt format correction if rejected due to format issue
            if not cleaned and rejection_reason:
                logger.warning(f"LLM response rejected: {rejection_reason}, attempting format correction")
                corrected = self._retry_with_format_correction(original_content, rejection_reason)
                if corrected:
                    # Re-validate corrected content
                    cleaned, _ = self._clean_code_response(
                        corrected,
                        error_category="compile",
                        db=None,
                        run_id=None,
                        family=None,
                        example_id=None,
                    )
                    response.content = cleaned
                    if cleaned:
                        logger.info(f"Format correction successful for rejection: {rejection_reason}")

        return response
    
    def _fix_runtime_code(
        self,
        code: str,
        error_logs: str,
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
        test_data_info: Optional[str] = None,
        family_config: Optional[Dict[str, Any]] = None,
        scaffolding_hints: Optional[List[str]] = None,
        section_heading: Optional[str] = None,
        description_context: Optional[str] = None,
        topic: Optional[str] = None,
        original_code: Optional[str] = None,
        catalog=None,
    ) -> LLMResponse:
        """Fix runtime errors with enhanced context and minimal-change rules."""

        # Build topic context for minimal-change guidance
        topic_context = topic or "demonstrating the API usage"

        system_prompt = f"""You are an expert C# developer fixing code examples in documentation.

CRITICAL RULES - FOLLOW EXACTLY:
1. Make MINIMAL changes - only fix the specific runtime error, nothing more
2. Do NOT add new functionality or code beyond what's absolutely needed
3. Do NOT refactor, improve, optimize, or expand the code
4. Keep the code focused on its ORIGINAL PURPOSE: {topic_context}
5. The code must remain relevant to the documentation context
6. Return ONLY valid C# code - no explanations, no markdown formatting

ALLOWED FIXES (in order of preference):
- Update file paths to use available test data files
- Add minimal null checks ONLY if required by the specific error
- Fix the specific exception cause

DO NOT:
- Add comprehensive error handling
- Add try-catch blocks unless absolutely necessary
- Change the code structure or logic
- Add comments or documentation
- Add features or functionality

If the error shows "Build failed:" this is a COMPILATION error, not a runtime error.
For build errors, add missing 'using' statements or fix syntax issues.

If you cannot fix the code without major changes, return the original code unchanged."""

        prompt_parts = [
            "Fix the following C# code that has runtime errors.",
        ]

        # Add content context prominently at the top
        if section_heading or description_context:
            prompt_parts.extend([
                "",
                "## DOCUMENTATION CONTEXT (the code must remain relevant to this):",
            ])
            if section_heading:
                prompt_parts.append(f"Section: {section_heading}")
            if description_context:
                prompt_parts.append(f"Description: {description_context[:500]}")

        # Add original code section if provided and different from current code
        if original_code and original_code.strip() != code.strip():
            prompt_parts.extend([
                "",
                "## Original Code (teaching intent reference):",
                "```csharp",
                original_code,
                "```",
                "",
                "**CRITICAL**: The original code demonstrates a specific concept/feature.",
                "Your fix MUST preserve this teaching intent.",
                "Do NOT add features, error handling, or complexity beyond what's needed to make it compile/run.",
            ])

        prompt_parts.extend([
            "",
            "## Current Code (to be fixed):",
            "```csharp",
            code,
            "```",
            "",
            "## Runtime Error:",
            "```",
            error_logs,
            "```",
        ])

        # Add Fix Instructions
        prompt_parts.extend([
            "",
            "## Fix Instructions:",
            "1. **Minimal Changes**: Make ONLY the changes needed to fix the errors",
            "2. **Preserve Intent**: The fixed code must demonstrate the SAME concept as the original",
            "3. **No Scope Creep**: Do NOT add error handling, validation, or features not in the original",
            "4. **Teaching Clarity**: A reader should understand the same lesson from your fix",
        ])

        # Add BAD fixes examples (including semantic drift prevention)
        prompt_parts.extend([
            "",
            "## Examples of BAD fixes (scope creep and semantic drift):",
            "- Adding try-catch blocks when original had none",
            "- Adding File.Exists() checks when original assumed file exists",
            "- Adding complex error messages when original used simple code",
            "- Restructuring code into methods when original was inline",
            "- Changing enum values (e.g., DecodeType.Code39 to DecodeType.DataMatrix)",
            "- Removing property customizations (e.g., deleting BarColor, BackColor assignments)",
            "- Changing constructor types (e.g., BarcodeGenerator to BarCodeReader)",
            "- Switching API modes (e.g., generation to recognition, save to load)",
        ])

        # Add GOOD fixes examples
        prompt_parts.extend([
            "",
            "## Examples of GOOD fixes (minimal):",
            "✅ Adding missing using statement",
            "✅ Fixing typo in variable name",
            "✅ Correcting API method signature",
            "✅ Adding namespace qualification",
        ])

        if test_data_info:
            prompt_parts.extend([
                "",
                "## Available Test Data Files:",
                test_data_info,
                "",
                "CRITICAL FILE PATH RULES:",
                "1. Replace only read-side placeholder paths (input/template/sample/fixture) with actual test files from above",
                "2. NEVER rewrite a save/output/generated destination to a fixture-like or template-like filename",
                "3. File aliases apply only to read-side paths; preserve the original source/output role of each path",
                "4. Use relative paths from the workspace directory - DO NOT use absolute paths",
                "5. Examples of placeholder -> real file transformations:",
                "   BAD: 'parent.zip' -> GOOD: use real file from alias mapping",
                "   BAD: 'path\\\\to\\\\input.zip' -> GOOD: use real file from available list",
                "   BAD: 'C:\\\\data\\\\archive.zip' -> GOOD: 'archive.zip' (if available)",
                "   BAD: 'input_folder' -> GOOD: use real directory from alias mapping",
                "   BAD: 'output.docx' -> GOOD: keep an output filename; do not replace it with 'Blank.docx'",
            ])

        # Inject API context from error analysis if not already provided
        injected_api_context = ""
        if not api_context and error_logs:
            injected_api_context = self._get_api_context_for_error(
                self._extract_error_code_from_logs(error_logs) or "UNKNOWN",
                error_logs
            )

        # Use either passed-in context or injected context
        final_api_context = api_context or injected_api_context
        if final_api_context:
            prompt_parts.extend([
                "",
                "## Relevant API Documentation:",
                final_api_context,
            ])

        # Inject targeted catalog context for this specific error (TASK-DLL-07)
        if catalog:
            error_code = self._extract_error_code_from_logs(error_logs) or "UNKNOWN"
            catalog_context = self._build_catalog_context(error_code, error_logs, catalog)
            if catalog_context:
                prompt_parts.extend([
                    "",
                    "## Exact API Reference (from assembly catalog):",
                    catalog_context,
                ])

        if similar_examples:
            prompt_parts.extend([
                "",
                "## Similar Working Examples (use as reference):",
            ])
            for i, example in enumerate(similar_examples[:3], 1):
                prompt_parts.extend([
                    f"### Example {i}:",
                    "```csharp",
                    example,
                    "```",
                ])

        prompt_parts.extend([
            "",
            "Return ONLY the corrected code. Make MINIMAL changes - fix only what's broken:",
        ])

        response = self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            max_tokens=4096,
            error_logs=error_logs,  # Pass error logs for complexity-based routing
        )

        # Clean up response - remove markdown code blocks if present
        # Note: Using new validation with format correction retry
        if response.success and response.content:
            original_content = response.content
            cleaned, rejection_reason = self._clean_code_response(
                response.content,
                error_category="runtime",
                db=None,  # Not available in this context
                run_id=None,
                family=None,
                example_id=None,
            )
            response.content = cleaned

            # Optional: Attempt format correction if rejected due to format issue
            if not cleaned and rejection_reason:
                logger.warning(f"LLM response rejected: {rejection_reason}, attempting format correction")
                corrected = self._retry_with_format_correction(original_content, rejection_reason)
                if corrected:
                    # Re-validate corrected content
                    cleaned, _ = self._clean_code_response(
                        corrected,
                        error_category="compile",
                        db=None,
                        run_id=None,
                        family=None,
                        example_id=None,
                    )
                    response.content = cleaned
                    if cleaned:
                        logger.info(f"Format correction successful for rejection: {rejection_reason}")

        return response
    
    def _validate_code_response(self, content: str, error_category: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate that LLM response looks like actual C# code.

        This prevents accepting prose explanations or malformed responses
        as valid code fixes. Validation is deterministic and category-aware.

        Args:
            content: The cleaned response content
            error_category: Optional error category for category-specific validation

        Returns:
            Tuple of (is_valid, rejection_reason)
            - is_valid: True if content appears to be valid C# code
            - rejection_reason: String describing why rejected, or None if valid
        """
        if not content or not content.strip():
            return (False, "empty_response")

        content = content.strip()

        # Check for common LLM refusal patterns FIRST (highest priority)
        refusal_patterns = [
            "I cannot", "I can't", "I'm unable", "I apologize",
            "As an AI", "I don't have", "I'm sorry"
        ]
        if any(pattern.lower() in content[:100].lower() for pattern in refusal_patterns):
            return (False, "llm_refusal_detected")

        # Reject if it looks like prose (starts with common explanation patterns)
        prose_patterns = [
            'I ', "I'm ", 'The ', 'This ', 'Here ', 'To ', 'You ',
            'Sorry', 'Unfortunately', 'Note:', 'Note that',
        ]
        first_word = content.split()[0] if content.split() else ""
        if any(content.startswith(p) for p in prose_patterns):
            return (False, "prose_explanation_detected")

        # Category-aware validation rules
        min_indicators = 2  # Default
        if error_category == "missing_type":
            # For missing type errors, expect 'using' statements
            min_indicators = 1
        elif error_category == "top_level_statements_error":
            # For top-level statement errors, expect class/Main wrapper
            if 'class ' not in content or 'Main' not in content:
                return (False, "missing_class_wrapper")

        # Must contain at least some code indicators
        code_indicators = [
            'using ', 'class ', 'void ', 'public ', 'private ',
            'static ', 'new ', '(', ')', '{', '}', ';',
            'var ', 'string ', 'int ', 'bool ', 'return ',
        ]
        indicator_count = sum(1 for ind in code_indicators if ind in content)

        # Require minimum code indicators to be considered code
        if indicator_count < min_indicators:
            return (False, f"insufficient_code_indicators ({indicator_count}/{min_indicators})")

        return (True, None)

    def _clean_code_response(
        self,
        content: str,
        error_category: Optional[str] = None,
        db: Optional[Any] = None,
        run_id: Optional[str] = None,
        family: Optional[str] = None,
        example_id: Optional[str] = None,
    ) -> tuple[str, Optional[str]]:
        """
        Remove markdown code blocks from LLM response and validate.

        Args:
            content: Raw LLM response content
            error_category: Optional error category for category-aware validation
            db: Optional database instance for telemetry tracking
            run_id: Optional run ID for telemetry
            family: Optional family for telemetry
            example_id: Optional example ID for telemetry

        Returns:
            Tuple of (cleaned_content, rejection_reason)
            - cleaned_content: Cleaned code string (empty if rejected)
            - rejection_reason: String describing why rejected, or None if valid
        """
        content = content.strip()

        # Track whether we removed markdown formatting
        had_markdown = False
        if content.startswith("```"):
            had_markdown = True
            lines = content.split("\n")
            # Remove first line (```csharp or ```)
            if lines:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        # Validate that the response looks like code
        is_valid, rejection_reason = self._validate_code_response(content, error_category)

        if not is_valid:
            # Track rejection with telemetry
            rejection_details = {
                'reason': rejection_reason,
                'had_markdown': had_markdown,
                'error_category': error_category,
                'content_length': len(content),
                'content_preview': content[:200] if content else '',
            }

            # Emit telemetry event if database is available
            if db and run_id and family:
                self._track_llm_rejection(
                    db=db,
                    run_id=run_id,
                    family=family,
                    example_id=example_id,
                    rejection_reason=rejection_reason,
                    rejection_details=rejection_details,
                )
            else:
                # Log rejection even without telemetry
                logger.warning(
                    f"LLM response rejected: {rejection_reason} "
                    f"(category={error_category}, had_markdown={had_markdown})"
                )

            # Return empty string to trigger retry, with rejection reason
            return ("", rejection_reason)

        return (content, None)

    def _retry_with_format_correction(
        self,
        original_content: str,
        rejection_reason: str,
    ) -> Optional[str]:
        """
        Attempt to fix format issues with a deterministic format correction prompt.

        This is a special retry for format-related rejections like:
        - prose_explanation_detected
        - insufficient_code_indicators
        - llm_refusal_detected

        Args:
            original_content: The rejected LLM response
            rejection_reason: Why it was rejected

        Returns:
            Corrected code string, or None if correction failed
        """
        # Only retry format issues
        format_issues = [
            "prose_explanation_detected",
            "insufficient_code_indicators",
            "llm_refusal_detected",
        ]

        if rejection_reason not in format_issues:
            return None

        # Deterministic format correction prompt
        system_prompt = """You are a code extraction expert.
Your ONLY job is to extract valid C# code from text.
Return ONLY the C# code, nothing else - no explanations, no markdown, no commentary."""

        prompt = f"""Extract ONLY the C# code from this text.

Input text:
{original_content[:1000]}

Rules:
1. Return ONLY C# code
2. Remove ALL explanatory text, prose, comments about what you're doing
3. Remove markdown code fences if present
4. Do NOT add explanations

Return the C# code now:"""

        try:
            response = self.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=2048,
                temperature=0.0,  # Deterministic
            )

            if response.success and response.content:
                # Clean without validation to avoid recursion
                content = response.content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    if lines:
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    content = "\n".join(lines)

                return content if content else None

        except Exception as e:
            logger.warning(f"Format correction retry failed: {e}")

        return None

    def _track_llm_rejection(
        self,
        db: Any,
        run_id: str,
        family: str,
        example_id: Optional[str],
        rejection_reason: str,
        rejection_details: Dict[str, Any],
    ) -> None:
        """
        Track LLM response rejection in telemetry and failure_details.

        Ensures no silent rejections by:
        1. Emitting telemetry event: llm_response_rejected
        2. Inserting row in failure_details table

        Args:
            db: Database instance
            run_id: Pipeline run ID
            family: Product family
            example_id: Optional example ID
            rejection_reason: Short reason code (e.g., "empty_response")
            rejection_details: Full structured details
        """
        from datetime import datetime, timezone
        from .models import TelemetryEvent

        try:
            # 1. Emit telemetry event
            event = TelemetryEvent(
                run_id=run_id,
                family=family,
                event_type="llm_response_rejected",
                phase="validation",
                example_id=example_id,
                duration_ms=0,
                success=False,
                metadata={
                    'rejection_reason': rejection_reason,
                    **rejection_details,
                },
                timestamp=datetime.now(timezone.utc),
            )
            db.save_telemetry_event(event)

            # 2. Insert failure_details row using new failure tracking API
            from ..pipeline.failure_tracker import track_llm_rejection
            track_llm_rejection(
                db=db,
                run_id=run_id,
                phase="validation",
                example_id=example_id,
                rejection_reason=rejection_reason,
                metadata=rejection_details,
            )

            logger.info(
                f"Tracked LLM rejection: {rejection_reason} "
                f"(example={example_id}, run={run_id[:8]})"
            )

        except Exception as e:
            # Don't fail the pipeline if telemetry fails, but log loudly
            logger.error(f"Failed to track LLM rejection telemetry: {e}")


    def review_markdown_structured(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
        catalog=None,
        family: str = None,
        article_intent: Optional[str] = None,
        review_context: Optional[str] = None,
        content_type: str = "",
    ) -> Dict[str, Any]:
        """
        Review markdown with GUARANTEED structured output using Instructor.

        Uses Pydantic models to enforce schema compliance, eliminating
        JSON parsing errors. Falls back to manual parsing if Instructor
        is unavailable.

        Args:
            markdown_content: Full markdown file content
            code_snippets: List of code snippets with context
                Each snippet should have: code, example_id, line, language
            catalog: Optional API catalog service
            family: Family identifier for catalog-based validation (e.g., 'ocr', 'zip', 'words')
            article_intent: Optional compact intent string from YAML frontmatter (title + description + steps)

        Returns:
            Structured dictionary with:
                - approved: bool
                - issues: List of issue dicts with validated types
                - raw_response: str (the LLM's raw response)
                - confidence: str (high/medium/low based on method used)
        """
        if not self._client:
            return {
                'approved': False,
                'issues': [],
                'raw_response': '',
                'error': 'LLM client not initialized',
                'confidence': 'none',
            }

        # Use Instructor if available for guaranteed schema compliance
        if INSTRUCTOR_AVAILABLE:
            return self._review_with_instructor(
                markdown_content,
                code_snippets,
                catalog=catalog,
                family=family,
                article_intent=article_intent,
                review_context=review_context,
            )
        else:
            logger.warning("Instructor not available, falling back to manual JSON parsing")
            return self._review_with_manual_parsing(
                markdown_content,
                code_snippets,
                catalog=catalog,
                family=family,
                article_intent=article_intent,
                review_context=review_context,
            )

    def _review_with_instructor(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
        catalog=None,
        family: str = None,
        article_intent: Optional[str] = None,
        review_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Review using Instructor for guaranteed schema compliance.

        This method uses Pydantic models to enforce the response schema,
        with automatic retries on validation failure.

        Args:
            family: Family identifier for catalog-based validation (e.g., 'ocr', 'zip', 'words')
            article_intent: Optional compact intent string from YAML frontmatter
        """
        system_prompt = """You are a technical documentation reviewer specializing in code example quality.

Your task is to verify code snippets in markdown documentation are:
1. Syntactically correct and complete
2. Relevant to the surrounding documentation context
3. Properly formatted with correct language tags
4. Free from security concerns or anti-patterns
5. Semantically aligned — the code actually achieves what the article's intent states.
   Flag intent_mismatch (severity: error) if a step in the article intent is contradicted or silently omitted.
6. Using the best available API — flag outdated_api (severity: warning) if the catalog
   shows a dedicated method/property that replaces the approach used.

Issue type definitions:
- syntax_error: Code has syntax errors or won't compile
- missing_context: Code is missing necessary setup or context
- incomplete_code: Code snippet is truncated or incomplete
- api_mismatch: Code uses deprecated or incorrect API calls
- security_concern: Code has potential security issues
- formatting_issue: Code formatting or language tag is wrong
- documentation_gap: Code doesn't match what documentation describes
- intent_mismatch: Code is technically correct but does not achieve what the article claims
- outdated_api: A more idiomatic or dedicated API exists per the catalog
- other: Other issues not in categories above

Severity definitions:
- info: Minor observation, not blocking
- warning: Should be addressed but not critical
- error: Must be fixed before publishing
- critical: Severe issue requiring immediate attention

CRITICAL: You MUST respond with a JSON object matching this EXACT schema:
{
  "approved": boolean,
  "issues": [
    {
      "snippet_index": integer (0-based index of code snippet),
      "issue_type": "syntax_error"|"missing_context"|"incomplete_code"|"api_mismatch"|"security_concern"|"formatting_issue"|"documentation_gap"|"intent_mismatch"|"outdated_api"|"other",
      "description": "string (minimum 10 characters)",
      "suggestion": "string or null",
      "severity": "info"|"warning"|"error"|"critical"
    }
  ]
}

Do NOT wrap the response in markdown code blocks. Do NOT include explanatory text before or after the JSON.
ONLY return the JSON object itself. If the code is fine, return: {"approved": true, "issues": []}"""

        prompt_parts = [
            "Review the following markdown document with code snippets:",
            "",
            "## Markdown Content:",
            markdown_content[:8000],  # Truncate for context window
            "",
            "## Code Snippets to Verify:",
        ]

        for i, snippet in enumerate(code_snippets[:10], 0):  # Up to 10 snippets
            prompt_parts.extend([
                f"### Snippet {i} (example_id: {snippet.get('example_id', 'unknown')}, line {snippet.get('line', 'unknown')}):",
                "```" + snippet.get('language', 'csharp'),
                snippet.get('code', ''),
                "```",
            ])

        prompt_parts.append("")

        # Add article intent if available
        if article_intent:
            prompt_parts.append("## Article Intent (from frontmatter):")
            prompt_parts.append(article_intent)
            prompt_parts.append("")

        family_review_hints = self._build_family_review_hints(
            family=family,
            code_snippets=code_snippets,
            article_intent=article_intent or "",
            markdown_content=markdown_content,
            content_type=content_type,
        )
        if family_review_hints:
            prompt_parts.append("## Family Review Hints:")
            prompt_parts.append(family_review_hints)
            prompt_parts.append("")

        # Add catalog context if available
        if catalog:
            catalog_context = self._build_catalog_context_for_review(catalog)
            if catalog_context:
                prompt_parts.append("## API Catalog Context:")
                prompt_parts.append(catalog_context)
                prompt_parts.append("")

        if review_context:
            prompt_parts.append("## Deterministic Review Context:")
            prompt_parts.append(review_context)
            prompt_parts.append("")

        prompt_parts.extend([
            "Review these snippets and provide your assessment.",
            "",
            "RESPONSE FORMAT REQUIREMENT:",
            "Return ONLY a JSON object with 'approved' (boolean) and 'issues' (array).",
            "Each issue must have: snippet_index (int), issue_type (enum), description (string), suggestion (string/null), severity (enum).",
            "Do NOT wrap in markdown. Do NOT add explanatory text. ONLY the JSON object.",
        ])

        try:
            # Wrap client with Instructor for structured outputs
            # Use Mode.JSON to bypass tool_call mechanism entirely.
            # Mode.TOOLS fails with OpenAI-compatible providers that return
            # multiple tool_calls (Instructor asserts exactly 1).
            # Mode.JSON uses response_format={"type":"json_object"} instead.
            _instructor_mode = instructor.Mode.JSON
            client = instructor.from_openai(self._client, mode=_instructor_mode)

            # Make the request with automatic schema enforcement
            _instructor_start = time.time()

            # Build request parameters
            request_params = {
                "model": self.model,
                "response_model": ReviewResponse,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "\n".join(prompt_parts)},
                ],
                "max_retries": 3,  # Automatic retry on validation failure
                "temperature": 0,  # Deterministic for consistency
            }

            response = client.chat.completions.create(**request_params)
            _instructor_latency = int((time.time() - _instructor_start) * 1000)

            # Capture for telemetry (Instructor doesn't expose raw usage)
            self._last_response = LLMResponse(
                content=response.model_dump_json() if hasattr(response, 'model_dump_json') else str(response),
                model=self.model,
                usage={},
                finish_reason="stop",
                latency_ms=_instructor_latency,
                success=True,
            )

            # Map snippet indices to example IDs
            processed_issues = []
            for issue in response.issues:
                example_id = 'unknown'
                if 0 <= issue.snippet_index < len(code_snippets):
                    example_id = code_snippets[issue.snippet_index].get('example_id', 'unknown')

                processed_issues.append({
                    'example_id': example_id,
                    'issue_type': issue.issue_type.value,
                    'description': issue.description,
                    'suggestion': issue.suggestion,
                    'severity': issue.severity.value,
                })

            # TASK-FIX-REVIEW-03: Filter out false-positive API mismatches using catalog
            if family:
                legitimate_issues = [
                    issue for issue in processed_issues
                    if self._validate_api_mismatch_against_catalog(issue, family)
                ]
                filtered_count = len(processed_issues) - len(legitimate_issues)
                if filtered_count > 0:
                    logger.info(f"[{family}] Filtered {filtered_count} false-positive API mismatch issues using catalog validation")
                processed_issues = legitimate_issues

            logger.info(f"Instructor review succeeded (mode={_instructor_mode.value})")
            return {
                'approved': response.approved,
                'issues': processed_issues,
                'raw_response': response.model_dump_json(),
                'confidence': 'high',  # Instructor guarantees valid response
            }

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(
                f"Instructor review failed (mode={_instructor_mode.value}): "
                f"{error_type}: {error_msg}. Model: {self.model}."
            )
            logger.debug("Full Instructor error traceback:", exc_info=True)

            # Fallback chain: Mode.JSON -> Mode.JSON_SCHEMA -> manual parsing
            if _instructor_mode == instructor.Mode.JSON:
                try:
                    logger.info("Retrying with instructor Mode.JSON_SCHEMA")
                    client2 = instructor.from_openai(self._client, mode=instructor.Mode.JSON_SCHEMA)
                    request_params_retry = {
                        "model": self.model,
                        "response_model": ReviewResponse,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": "\n".join(prompt_parts)},
                        ],
                        "max_retries": 2,
                        "temperature": 0,
                    }
                    response = client2.chat.completions.create(**request_params_retry)
                    _instructor_latency = int((time.time() - _instructor_start) * 1000)
                    self._last_response = LLMResponse(
                        content=response.model_dump_json() if hasattr(response, 'model_dump_json') else str(response),
                        model=self.model, usage={}, finish_reason="stop",
                        latency_ms=_instructor_latency, success=True,
                    )
                    processed_issues = []
                    for issue in response.issues:
                        example_id = 'unknown'
                        if 0 <= issue.snippet_index < len(code_snippets):
                            example_id = code_snippets[issue.snippet_index].get('example_id', 'unknown')
                        processed_issues.append({
                            'example_id': example_id,
                            'issue_type': issue.issue_type.value,
                            'description': issue.description,
                            'suggestion': issue.suggestion,
                            'severity': issue.severity.value,
                        })
                    if family:
                        legitimate_issues = [
                            issue for issue in processed_issues
                            if self._validate_api_mismatch_against_catalog(issue, family)
                        ]
                        filtered_count = len(processed_issues) - len(legitimate_issues)
                        if filtered_count > 0:
                            logger.info(f"[{family}] Filtered {filtered_count} false-positive API mismatch issues using catalog validation")
                        processed_issues = legitimate_issues
                    logger.info("Instructor review succeeded (mode=JSON_SCHEMA, fallback)")
                    return {
                        'approved': response.approved,
                        'issues': processed_issues,
                        'raw_response': response.model_dump_json(),
                        'confidence': 'high',
                    }
                except Exception as e2:
                    logger.warning(
                        f"Instructor JSON_SCHEMA fallback also failed: {type(e2).__name__}: {e2}. "
                        f"Falling back to manual parsing."
                    )

            # Final fallback: manual parsing
            return self._review_with_manual_parsing(
                markdown_content,
                code_snippets,
                catalog=catalog,
                family=family,
                article_intent=article_intent,
                review_context=review_context,
            )

    def _review_with_manual_parsing(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
        catalog=None,
        family: str = None,
        article_intent: Optional[str] = None,
        review_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fallback review method with manual JSON parsing.

        Used when Instructor is unavailable or fails.

        Args:
            family: Family identifier for catalog-based validation (e.g., 'ocr', 'zip', 'words')
            article_intent: Optional compact intent string from YAML frontmatter
        """
        system_prompt = """You are a technical documentation reviewer specializing in code example quality.

Your task is to verify code snippets in markdown documentation are:
1. Syntactically correct and complete
2. Relevant to the surrounding documentation context
3. Properly formatted with correct language tags
4. Free from security concerns or anti-patterns
5. Semantically aligned — the code actually achieves what the article's intent states.
   Flag intent_mismatch (severity: error) if a step in the article intent is contradicted or silently omitted.
6. Using the best available API — flag outdated_api (severity: warning) if the catalog
   shows a dedicated method/property that replaces the approach used.

Return a JSON object with the following structure:
{
    "approved": true/false,
    "issues": [
        {
            "snippet_index": 0,
            "issue_type": "syntax_error|missing_context|incomplete_code|api_mismatch|security_concern|formatting_issue|documentation_gap|intent_mismatch|outdated_api|other",
            "description": "Clear description of the issue",
            "suggestion": "Optional suggestion for fixing",
            "severity": "info|warning|error|critical"
        }
    ]
}

ONLY report actual issues. If the code is fine, return {"approved": true, "issues": []}"""

        prompt_parts = [
            "Review the following markdown document with code snippets:",
            "",
            "## Markdown Content:",
            markdown_content[:8000],
            "",
            "## Code Snippets to Verify:",
        ]

        for i, snippet in enumerate(code_snippets[:10], 0):
            prompt_parts.extend([
                f"### Snippet {i} (example_id: {snippet.get('example_id', 'unknown')}, line {snippet.get('line', 'unknown')}):",
                "```" + snippet.get('language', 'csharp'),
                snippet.get('code', ''),
                "```",
            ])

        # Add article intent if available
        if article_intent:
            prompt_parts.append("")
            prompt_parts.append("## Article Intent (from frontmatter):")
            prompt_parts.append(article_intent)

        family_review_hints = self._build_family_review_hints(
            family=family,
            code_snippets=code_snippets,
            article_intent=article_intent or "",
            markdown_content=markdown_content,
            content_type=content_type,
        )
        if family_review_hints:
            prompt_parts.append("")
            prompt_parts.append("## Family Review Hints:")
            prompt_parts.append(family_review_hints)

        if review_context:
            prompt_parts.append("")
            prompt_parts.append("## Deterministic Review Context:")
            prompt_parts.append(review_context)

        prompt_parts.extend([
            "",
            "Return your review as valid JSON only (no markdown formatting):",
        ])

        response = self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            max_tokens=4096,
        )

        # Default result
        result = {
            'approved': True,
            'issues': [],
            'raw_response': response.content if response.success else '',
            'llm_error': response.error if not response.success else None,
            'confidence': 'low',  # Manual parsing baseline (lower reliability than Instructor)
        }

        if not response.success:
            result['approved'] = False
            result['issues'] = [{
                'example_id': 'unknown',
                'issue_type': 'other',
                'description': f'LLM review failed: {response.error}',
                'suggestion': None,
                'severity': 'error',
            }]
            return result

        # Try to parse the JSON response
        try:
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines:
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            parsed = json.loads(content)
            result['approved'] = parsed.get('approved', True)
            # Successfully parsed, but downgrade from 'high' to 'medium' for manual parsing fallback
            result['confidence'] = 'medium'  # Penalty: 'high' -> 'medium' (Instructor not used)
            logger.info(f"Manual parsing confidence penalty applied: confidence={result['confidence']}")

            raw_issues = parsed.get('issues', [])
            processed_issues = []

            for issue in raw_issues:
                snippet_idx = issue.get('snippet_index', 0)
                example_id = 'unknown'
                if 0 <= snippet_idx < len(code_snippets):
                    example_id = code_snippets[snippet_idx].get('example_id', 'unknown')

                processed_issues.append({
                    'example_id': example_id,
                    'issue_type': issue.get('issue_type', 'other'),
                    'description': issue.get('description', 'No description provided'),
                    'suggestion': issue.get('suggestion'),
                    'severity': issue.get('severity', 'warning'),
                })

            # TASK-FIX-REVIEW-03: Filter out false-positive API mismatches using catalog
            if family:
                legitimate_issues = [
                    issue for issue in processed_issues
                    if self._validate_api_mismatch_against_catalog(issue, family)
                ]
                filtered_count = len(processed_issues) - len(legitimate_issues)
                if filtered_count > 0:
                    logger.info(f"[{family}] Filtered {filtered_count} false-positive API mismatch issues using catalog validation")
                processed_issues = legitimate_issues

            result['issues'] = processed_issues

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM review response as JSON: {e}")
            result['approved'] = False
            result['issues'] = [{
                'example_id': 'unknown',
                'issue_type': 'other',
                'description': f'Failed to parse LLM response: {str(e)}',
                'suggestion': 'Manual review required',
                'severity': 'warning',
            }]

        return result

    def _build_catalog_context_for_review(self, catalog) -> str:
        """Build compact catalog context for final review."""
        if not catalog or not catalog.is_loaded:
            return ""

        parts = []
        namespaces = catalog.get_all_namespaces()
        if namespaces:
            parts.append("Documented API Namespaces:")
            for ns in namespaces[:25]:
                parts.append(f"  - {ns}")

        parts.append("")
        parts.append("VALIDATION: Flag 'api_mismatch' if code uses types/namespaces NOT in this list.")
        return "\n".join(parts)

    def _build_family_review_hints(
        self,
        *,
        family: Optional[str],
        code_snippets: List[Dict[str, Any]],
        article_intent: str,
        markdown_content: str,
        content_type: str = "",
    ) -> str:
        if not family:
            return ""

        hints_path = Path("config/families") / f"{family}_review_hints.json"
        if not hints_path.exists():
            return ""

        try:
            raw_hints = json.loads(hints_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to load review hints for %s: %s", family, exc)
            return ""

        code_blob = "\n".join(snippet.get("code", "") for snippet in code_snippets)
        context_blob = "\n".join([article_intent, markdown_content[:4000]]).lower()
        selected: List[str] = []
        for hint in raw_hints:
            pattern = hint.get("pattern")
            if pattern and pattern not in code_blob:
                continue
            context_key = hint.get("context", "").lower()
            if context_key and context_key not in context_blob:
                continue
            allowed_types = hint.get("content_types")
            if allowed_types and content_type and content_type not in allowed_types:
                continue
            issue_type = hint.get("issue_type")
            prefix = f"[{issue_type}] " if issue_type else ""
            selected.append(f"- {prefix}{hint.get('hint', '').strip()}")

        if not selected:
            return ""
        header = "## Known-Wrong Patterns — Flag These Regardless of Article Intent:"
        preamble = (
            "IMPORTANT: The following are documented API misuses and false claims for this "
            "product family. If code matches any pattern below, flag it as an issue EVEN IF "
            "the article's stated intent or prose appears to justify the approach. "
            "The article itself may be wrong; these constraints take precedence over article intent."
        )
        return header + "\n" + preamble + "\n" + "\n".join(selected[:8])

    def review_prose_against_code(
        self,
        *,
        prose_text: str,
        code_text: str,
        article_intent: str = "",
        section_heading: str = "",
        family_hints: str = "",
    ) -> Dict[str, Any]:
        """Audit whether prose accurately describes adjacent code, with optional corrected prose."""
        if not self._client:
            return {"accurate": True, "issues": "", "corrected_prose": None, "success": False, "error": "LLM client not initialized"}

        system_prompt = """You review technical prose against adjacent C# code.

Return valid JSON with:
- accurate: boolean
- issues: short string
- corrected_prose: string or null

Rules:
- accurate=true if the prose is materially correct
- corrected_prose must be concise and preserve the author's meaning
- If prose is already accurate, return corrected_prose as null
- Return JSON only
"""

        prompt_parts = [
            "Assess whether this prose accurately describes the adjacent code.",
            "",
        ]
        if section_heading:
            prompt_parts.extend(["Section:", section_heading, ""])
        if article_intent:
            prompt_parts.extend(["Article intent:", article_intent, ""])
        prompt_parts.extend(
            [
                "Prose:",
                prose_text,
                "",
                "Code:",
                "```csharp",
                code_text,
                "```",
                "",
                'Return JSON only: {"accurate": true|false, "issues": "...", "corrected_prose": "..." or null}',
            ]
        )

        if family_hints:
            prompt_parts.append("")
            prompt_parts.append("## Family Knowledge Constraints:")
            prompt_parts.append(family_hints)
            prompt_parts.append(
                "Use the above to identify factually incorrect claims in the prose "
                "even if the claim seems internally consistent with the adjacent code."
            )

        response = self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            temperature=0,
            max_tokens=1200,
        )
        if not response.success:
            return {"accurate": True, "issues": "", "corrected_prose": None, "success": False, "error": response.error}

        content = response.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
            return {
                "accurate": bool(parsed.get("accurate", True)),
                "issues": parsed.get("issues", ""),
                "corrected_prose": parsed.get("corrected_prose"),
                "success": True,
                "error": None,
            }
        except Exception as exc:
            logger.warning("Failed to parse prose review JSON: %s", exc)
            return {
                "accurate": True,
                "issues": "",
                "corrected_prose": None,
                "success": False,
                "error": str(exc),
            }

    def _load_api_catalog(self, family: str) -> dict:
        """
        Load API catalog for ANY family (GENERIC).

        TASK-FIX-REVIEW-03: Generic catalog loader that works with all Aspose families.

        Args:
            family: Family identifier (e.g., 'ocr', 'zip', 'words', 'cells', 'barcode', 'pdf')

        Returns:
            Catalog dict with 'types', 'namespaces', 'enums', 'properties', etc.
            Returns empty dict structure if catalog not found.
        """
        catalog_path = f"config/families/{family}_api_catalog.json"

        # Check if file exists
        if not os.path.exists(catalog_path):
            logger.warning(f"API catalog not found for family '{family}': {catalog_path}")
            return {'types': {}, 'namespaces': [], 'enums': {}, 'properties': {}}

        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
                logger.debug(f"[{family}] Loaded API catalog from {catalog_path}")
                return catalog
        except Exception as e:
            logger.warning(f"Failed to load API catalog for family '{family}': {e}")
            return {'types': {}, 'namespaces': [], 'enums': {}, 'properties': {}}

    def _validate_api_mismatch_against_catalog(self, issue: dict, family: str) -> bool:
        """
        GENERIC: Returns True if issue is legitimate, False if false positive.

        TASK-FIX-REVIEW-03: Cross-validates API mismatch issues against installed catalog.
        Works with ZIP, Words, Cells, Barcode, OCR, PDF, etc.

        Args:
            issue: Issue dict with 'issue_type', 'description', etc.
            family: Family identifier (e.g., 'ocr', 'zip', 'words')

        Returns:
            True if issue is legitimate (keep it)
            False if issue is false positive (filter it out)
        """
        # Only validate api_mismatch issues
        if issue.get('issue_type') != 'api_mismatch':
            return True

        # Load catalog for this family
        catalog = self._load_api_catalog(family)
        if not catalog.get('types'):
            # No catalog available, keep the issue (conservative)
            return True

        description = issue.get('description', '')

        # Extract API references from description (e.g., "Language.Eng", "Document.Save", "result.FileName")
        # Pattern: Word.Word or Word.Word.Word chains
        import re
        api_refs = re.findall(r'\b([A-Z][a-zA-Z0-9]+(?:\.[A-Z][a-zA-Z0-9]+)+)\b', description)

        if not api_refs:
            # No API references found, keep the issue
            return True

        # Check each API reference against catalog
        for api_ref in api_refs:
            parts = api_ref.split('.')
            type_name = parts[0]  # First part is the type (e.g., "Language", "Document", "result")

            # Check if type exists in catalog
            # catalog['types'] is a dict: {"TypeName": "Namespace", ...}
            type_found = False

            # Direct type name match
            if type_name in catalog.get('types', {}):
                type_found = True
            else:
                # Check full names (types might be stored with namespace prefix)
                for cat_type_name, cat_namespace in catalog.get('types', {}).items():
                    if cat_type_name == type_name:
                        type_found = True
                        break

            # If type found, check if it has the referenced member (enum, property, method)
            if type_found and len(parts) > 1:
                member_name = parts[1]  # Second part is the member (e.g., "Eng", "Save", "FileName")

                # Check in enums
                if type_name in catalog.get('enums', {}):
                    enum_values = catalog['enums'][type_name]
                    if member_name.upper() in [v.upper() for v in enum_values]:
                        logger.info(
                            f"[{family}] API mismatch false positive: {api_ref} "
                            f"(enum {type_name}.{member_name} exists in catalog)"
                        )
                        return False

                # Check in properties
                if type_name in catalog.get('properties', {}):
                    properties = catalog['properties'][type_name]
                    if member_name in properties:
                        logger.info(
                            f"[{family}] API mismatch false positive: {api_ref} "
                            f"(property {type_name}.{member_name} exists in catalog)"
                        )
                        return False

                # Check in methods (if catalog has key_methods)
                if type_name in catalog.get('key_methods', {}):
                    methods = catalog['key_methods'][type_name]
                    # Methods might be stored as list of dicts with 'name' key or list of strings
                    if isinstance(methods, list):
                        # List of method dicts: [{'name': 'MethodName', ...}, ...]
                        method_names = set()
                        for m in methods:
                            if isinstance(m, dict) and 'name' in m:
                                method_names.add(m['name'])
                            elif isinstance(m, str):
                                method_names.add(m)

                        if member_name in method_names:
                            logger.info(
                                f"[{family}] API mismatch false positive: {api_ref} "
                                f"(method {type_name}.{member_name} exists in catalog)"
                            )
                            return False
                    elif isinstance(methods, dict):
                        # Dict of methods: {'MethodName': {...}, ...}
                        if member_name in methods:
                            logger.info(
                                f"[{family}] API mismatch false positive: {api_ref} "
                                f"(method {type_name}.{member_name} exists in catalog)"
                            )
                            return False

        # Issue passed validation - keep it
        return True

    def final_review(
        self,
        original_code: str,
        fixed_code: str,
        signature_drift: Optional[Dict[str, Any]] = None,
        catalog=None,
    ) -> Dict[str, Any]:
        """
        Review fixed code to verify it preserves the original intent.

        This is Stage 5.5 in the pipeline - after code compiles successfully,
        verify that LLM fixes didn't change the functionality.

        Args:
            original_code: The original code (intent source)
            fixed_code: The code after LLM fixes
            signature_drift: Optional semantic signature drift data from Gate 1

        Returns:
            Dictionary with:
                - intent_preserved: bool (True if fixed code matches original intent)
                - confidence: float (0.0-1.0, confidence in the assessment)
                - explanation: str (Brief explanation of analysis)
                - drift_details: List[str] (Specific drift points if intent_preserved=False)
                - success: bool (True if review completed, False on error)
                - error: Optional[str] (Error message if success=False)
        """
        system_prompt = """You are a code review expert specializing in semantic equivalence analysis.

Your task is to determine if FIXED CODE preserves the intent and functionality of ORIGINAL CODE.

Key principles:
- intent_preserved=true: Fixed code does the same thing (minor syntax changes OK)
- intent_preserved=false: Fixed code has different functionality, missing features, or wrong logic
- Be strict: If unsure, mark intent_preserved=false
- Focus on semantic equivalence, not syntactic similarity

Examples of ALLOWED changes (intent_preserved=true):
- Adding missing 'using' statements
- Wrapping code in class/Main structure
- Adding proper disposal patterns (using blocks)
- Fixing type declarations
- Adding necessary null checks or error handling

Examples of FORBIDDEN changes (intent_preserved=false):
- Changing from Create to Extract operations
- Changing from Save to Load operations
- Adding/removing major functionality
- Changing API method calls
- Changing file paths or resources in significant ways
- Removing core logic or features
- Changing enum values (e.g., DecodeType.Code39 to DataMatrix, CompressionLevel change)
- Removing property customizations (e.g., BarColor, BackColor, Resolution assignments removed)
- Changing constructor types (e.g., BarcodeGenerator to BarCodeReader)
- Switching between generation and recognition APIs

Return ONLY valid JSON, no markdown formatting."""

        sig_context = ""
        if signature_drift:
            enum_changes = signature_drift.get('enum_changes', {})
            method_changes = signature_drift.get('method_changes', {})
            type_changes = signature_drift.get('type_changes', [])
            property_changes = signature_drift.get('property_changes', {})
            if enum_changes or type_changes or method_changes.get('removed') or property_changes.get('removed'):
                sig_context = f"""
## DETECTED SIGNATURE CHANGES (from automated analysis):
- Enum changes: {enum_changes if enum_changes else 'None'}
- Method changes: {method_changes if method_changes.get('added') or method_changes.get('removed') else 'None'}
- Type changes: {type_changes if type_changes else 'None'}
- Property changes: {property_changes if property_changes.get('removed') or property_changes.get('changed') else 'None'}

Pay special attention to these detected changes when assessing intent preservation.
"""

        prompt = f"""Analyze whether the FIXED CODE preserves the intent of the ORIGINAL CODE.

## ORIGINAL CODE (intent source):
```csharp
{original_code}
```

## FIXED CODE (after LLM fixes):
```csharp
{fixed_code}
```
{sig_context}
Respond with JSON in this exact format:
{{
  "intent_preserved": true or false,
  "confidence": 0.0 to 1.0,
  "explanation": "Brief explanation of your analysis",
  "drift_details": ["specific drift 1", "specific drift 2"]
}}

If intent_preserved=true, set drift_details to empty array.
If intent_preserved=false, provide specific examples of what changed.

Return ONLY the JSON object, no other text."""

        response = self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.0,  # Deterministic for consistency
        )

        # Default result on error
        default_result = {
            'intent_preserved': False,
            'confidence': 0.0,
            'explanation': 'Review failed',
            'drift_details': [],
            'success': False,
            'error': None,
        }

        if not response.success:
            default_result['error'] = response.error or 'LLM request failed'
            return default_result

        # Parse JSON response
        try:
            content = response.content.strip()

            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                if lines:
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            # Remove "json" language tag if present
            content = content.replace("```json", "").replace("```", "").strip()

            parsed = json.loads(content)

            # Validate required fields
            if 'intent_preserved' not in parsed:
                raise ValueError("Missing 'intent_preserved' field in response")
            if 'confidence' not in parsed:
                raise ValueError("Missing 'confidence' field in response")
            if 'explanation' not in parsed:
                raise ValueError("Missing 'explanation' field in response")

            result = {
                'intent_preserved': bool(parsed['intent_preserved']),
                'confidence': float(parsed['confidence']),
                'explanation': str(parsed['explanation']),
                'drift_details': parsed.get('drift_details', []),
                'success': True,
                'error': None,
            }

            # Validate confidence range
            if not 0.0 <= result['confidence'] <= 1.0:
                logger.warning(f"Invalid confidence value: {result['confidence']}, clamping to [0.0, 1.0]")
                result['confidence'] = max(0.0, min(1.0, result['confidence']))

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse final review JSON: {e}")
            logger.debug(f"Raw response: {response.content[:500]}")
            default_result['error'] = f"JSON parsing failed: {str(e)}"
            return default_result
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid final review response structure: {e}")
            default_result['error'] = f"Invalid response structure: {str(e)}"
            return default_result
        except Exception as e:
            logger.warning(f"Unexpected error in final review: {e}")
            default_result['error'] = f"Unexpected error: {str(e)}"
            return default_result

    def generate_semantic_fix(
        self,
        code: str,
        issue_type: str,
        issue_description: str,
        issue_suggestion: str,
        catalog_context: str = "",
        article_intent: str = "",
        section_heading: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a semantically corrected version of code based on a detected review issue.

        Unlike fix_code() (which is error-driven), this method is intent-driven:
        it takes a detected semantic issue (from Phase E review) and produces a
        corrected code block grounded in catalog-verified alternatives.

        Args:
            code: Current code block to fix
            issue_type: Issue category (e.g. "intent_mismatch", "api_mismatch", "outdated_api")
            issue_description: Human-readable description of the issue
            issue_suggestion: The review LLM's suggested fix (may be empty)
            catalog_context: Compact catalog context — related types, constructors, sibling types
            article_intent: The article's high-level intent (from DB article_intent field)
            section_heading: Markdown section heading above the code block

        Returns:
            Dictionary with:
                - fixed_code: str — corrected code (or original if fix not possible)
                - changed: bool — True if code was modified
                - explanation: str — what was changed and why
                - success: bool — True if call completed, False on error
                - error: Optional[str] — error message if success=False
        """
        default_result: Dict[str, Any] = {
            "fixed_code": code,
            "changed": False,
            "explanation": "",
            "success": False,
            "error": None,
        }

        system_prompt = """You are an expert C# code corrector specializing in Aspose product APIs.

Your task is to fix a SEMANTIC issue in a C# code block — the code compiles and runs, but it is
semantically incorrect, misleading, or uses wrong API choices.

Rules:
- Return ONLY the corrected code block — no markdown fences, no explanation in the code output
- Preserve the overall structure and purpose of the code
- Only change what is explicitly identified in the issue
- Use ONLY types and methods confirmed in the catalog context provided
- Do NOT hallucinate types or method signatures not listed in the catalog
- If the issue is ambiguous or you cannot determine the correct fix with confidence,
  return the original code unchanged

Return valid JSON with keys: fixed_code (string), explanation (string), changed (boolean)."""

        intent_section = f"\n## Article Intent\n{article_intent}\n" if article_intent else ""
        heading_section = f"\n## Section\n{section_heading}\n" if section_heading else ""
        catalog_section = f"\n## Catalog Context (catalog-verified types and alternatives)\n{catalog_context}\n" if catalog_context else ""
        suggestion_section = f"\n## Reviewer Suggestion\n{issue_suggestion}\n" if issue_suggestion else ""

        prompt = f"""Fix the semantic issue in the following C# code block.
{intent_section}{heading_section}
## Issue
Type: {issue_type}
Description: {issue_description}
{suggestion_section}{catalog_section}
## Current Code
```csharp
{code}
```

Return ONLY valid JSON in this exact format:
{{
  "fixed_code": "<corrected code here>",
  "explanation": "<what you changed and why>",
  "changed": true or false
}}

If you cannot determine the correct fix with confidence, set changed=false and return the original code in fixed_code."""

        try:
            response = self.complete(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=2000,
            )

            if not response.success:
                default_result["error"] = response.error
                return default_result

            # Parse JSON response
            content = response.content.strip()
            # Strip markdown fences if model wrapped in them
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            fixed_code = parsed.get("fixed_code", code)
            changed = bool(parsed.get("changed", False)) and fixed_code != code
            explanation = parsed.get("explanation", "")

            return {
                "fixed_code": fixed_code,
                "changed": changed,
                "explanation": explanation,
                "success": True,
                "error": None,
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse semantic fix JSON: {e}")
            default_result["error"] = f"JSON parsing failed: {str(e)}"
            return default_result
        except Exception as e:
            logger.warning(f"Unexpected error in generate_semantic_fix: {e}")
            default_result["error"] = f"Unexpected error: {str(e)}"
            return default_result


class LLMServiceFactory:
    """Factory for creating LLM service instances."""

    @staticmethod
    def from_config(
        config: Dict[str, Any],
        use_final_review: bool = False,
    ) -> LLMService:
        """
        Create LLM service from configuration dictionary.

        Args:
            config: Configuration dictionary with 'llm' and optionally 'final_review' sections
            use_final_review: If True, use final_review config instead of main llm config

        Returns:
            LLMService instance
        """
        if use_final_review and 'final_review' in config:
            # Use final_review configuration (C.6: separate provider/model/timeout)
            final_review_config = config['final_review']
            llm_config = config.get('llm', {})  # For fallback values

            # Determine API key based on provider
            provider = final_review_config.get('provider', 'openai')
            if provider == 'anthropic':
                api_key_env_var = 'ANTHROPIC_API_KEY'
            elif provider == 'openai':
                api_key_env_var = 'OPENAI_API_KEY'
            else:
                api_key_env_var = llm_config.get('api_key_env_var', 'OPENAI_API_KEY')

            return LLMService(
                provider=provider,
                model=final_review_config.get('model', 'claude-3-5-sonnet-latest'),
                api_key=os.getenv(api_key_env_var),
                base_url=final_review_config.get('base_url'),  # Allow base_url override
                temperature=0.0,  # Final review should be deterministic
                max_retries=1,  # Final review doesn't need retries
                retry_backoff_seconds=5,
                timeout_seconds=final_review_config.get('timeout_seconds', 30),
                seed=None,  # Final review doesn't use seed
                deterministic_mode=False,
                enforce_timeout=True,
            )
        else:
            # Use main llm configuration
            llm_config = config.get('llm', {})

            return LLMService(
                provider=llm_config.get('provider', 'openai'),
                model=llm_config.get('model', 'gpt-4o'),
                api_key=os.getenv(llm_config.get('api_key_env_var', 'OPENAI_API_KEY')),
                base_url=llm_config.get('base_url'),
                temperature=llm_config.get('temperature', 0.2),
                max_retries=llm_config.get('max_retries', 3),
                retry_backoff_seconds=llm_config.get('retry_backoff_seconds', 5),
                timeout_seconds=llm_config.get('timeout_seconds', 120),
                seed=llm_config.get('seed'),
                deterministic_mode=llm_config.get('deterministic_mode', False),
                enforce_timeout=llm_config.get('enforce_timeout', True),
            )
