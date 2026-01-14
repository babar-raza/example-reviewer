"""
LLM Service for Example Reviewer Pipeline.
Supports OpenAI-compatible models as required by the spec.
"""

import os
import time
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


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


class LLMService:
    """
    LLM adapter layer supporting OpenAI-compatible models.
    Follows spec requirement for single adapter supporting model switching via config.
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3,
        retry_backoff_seconds: int = 5,
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
        """
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        
        # Resolve API key from environment if not provided
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url
        
        # Initialize client
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the API client."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available. LLM features disabled.")
            return
        
        if self.provider in ("openai", "azure", "ollama", "openrouter"):
            client_kwargs = {}
            
            if self.api_key:
                client_kwargs["api_key"] = self.api_key
            
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            elif self.provider == "ollama":
                client_kwargs["base_url"] = "http://localhost:11434/v1"
                client_kwargs["api_key"] = "ollama"  # Ollama requires a placeholder
            
            self._client = OpenAI(**client_kwargs)
    
    def is_available(self) -> bool:
        """Check if LLM service is available."""
        return self._client is not None
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Override default temperature
            stop: Stop sequences
            
        Returns:
            LLMResponse with content and metadata
        """
        if not self._client:
            return LLMResponse(
                content="",
                model=self.model,
                usage={},
                finish_reason="error",
                latency_ms=0,
                success=False,
                error="LLM client not initialized"
            )
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        temp = temperature if temperature is not None else self.temperature
        
        last_error = None
        for attempt in range(self.max_retries):
            start_time = time.time()
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temp,
                    stop=stop,
                )
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                choice = response.choices[0]
                return LLMResponse(
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
                )
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
        
        return LLMResponse(
            content="",
            model=self.model,
            usage={},
            finish_reason="error",
            latency_ms=0,
            success=False,
            error=last_error or "Unknown error"
        )
    
    def fix_code(
        self,
        code: str,
        error_logs: str,
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
    ) -> LLMResponse:
        """
        Fix code using LLM.
        
        Args:
            code: Original code with errors
            error_logs: Compiler/runtime error output
            api_context: Relevant API documentation
            similar_examples: Similar working examples from vector DB
            
        Returns:
            LLMResponse with fixed code
        """
        system_prompt = """You are an expert C# developer specializing in fixing code errors.
Your task is to fix the provided code based on the error messages.
Return ONLY the corrected code without any explanations or markdown formatting.
Preserve the original code structure and style as much as possible."""

        prompt_parts = [
            "Fix the following C# code that has errors:",
            "",
            "## Original Code:",
            "```csharp",
            code,
            "```",
            "",
            "## Error Output:",
            "```",
            error_logs,
            "```",
        ]
        
        if api_context:
            prompt_parts.extend([
                "",
                "## Relevant API Documentation:",
                api_context,
            ])
        
        if similar_examples:
            prompt_parts.extend([
                "",
                "## Similar Working Examples (for reference):",
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
            "Return ONLY the corrected code, no explanations:",
        ])
        
        response = self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            max_tokens=4096,
        )
        
        # Clean up response - remove markdown code blocks if present
        if response.success and response.content:
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                # Remove first line (```csharp or ```)
                if lines:
                    lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response.content = "\n".join(lines)
        
        return response
    
    def review_markdown(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, str]],
    ) -> LLMResponse:
        """
        Review updated markdown for code relevance and correctness.
        
        Args:
            markdown_content: Full markdown file content
            code_snippets: List of code snippets with their context
            
        Returns:
            LLMResponse with review results
        """
        system_prompt = """You are a technical documentation reviewer.
Your task is to verify that code snippets in the markdown are:
1. Relevant to the surrounding documentation context
2. Properly formatted with correct language tags
3. Complete and syntactically correct

Return a JSON object with the following structure:
{
    "approved": true/false,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1"]
}"""

        prompt_parts = [
            "Review the following markdown document with code snippets:",
            "",
            "## Markdown Content:",
            markdown_content[:8000],  # Truncate for context window
            "",
            "## Code Snippets to Verify:",
        ]
        
        for i, snippet in enumerate(code_snippets[:5], 1):
            prompt_parts.extend([
                f"### Snippet {i} (at line {snippet.get('line', 'unknown')}):",
                "```" + snippet.get('language', 'csharp'),
                snippet.get('code', ''),
                "```",
            ])
        
        prompt_parts.extend([
            "",
            "Return your review as JSON:",
        ])
        
        return self.complete(
            prompt="\n".join(prompt_parts),
            system_prompt=system_prompt,
            max_tokens=2048,
        )


class LLMServiceFactory:
    """Factory for creating LLM service instances."""
    
    @staticmethod
    def from_config(config: Dict[str, Any]) -> LLMService:
        """Create LLM service from configuration dictionary."""
        llm_config = config.get('llm', {})
        
        return LLMService(
            provider=llm_config.get('provider', 'openai'),
            model=llm_config.get('model', 'gpt-4o'),
            api_key=os.getenv(llm_config.get('api_key_env_var', 'OPENAI_API_KEY')),
            base_url=llm_config.get('base_url'),
            temperature=llm_config.get('temperature', 0.2),
            max_retries=llm_config.get('max_retries', 3),
            retry_backoff_seconds=llm_config.get('retry_backoff_seconds', 5),
        )
