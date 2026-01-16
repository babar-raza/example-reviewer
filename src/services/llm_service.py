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

try:
    import instructor
    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False

from .llm_contracts import ReviewResponse, ReviewIssue, IssueType, Severity

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
        "missing_type": "Add the appropriate 'using' statement at the top. Common Aspose.Zip namespaces: Aspose.Zip, Aspose.Zip.Saving, Aspose.Zip.SevenZip, Aspose.Zip.Rar",
        "undefined_variable": "Declare the variable before use with proper type, or check if it's a typo",
        "missing_semicolon": "Add semicolon at the end of the statement",
        "missing_brace": "Add the missing closing brace }",
        "type_mismatch": "Use explicit casting or the correct type",
        "member_not_found": "Check the API documentation - the member may not exist or requires different syntax",
        "top_level_statements_error": "Wrap all code in 'class Program { static void Main() { ... } }' structure",
    }

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
            
            if self.provider == "ollama":
                # Ollama doesn't require a real API key
                client_kwargs["base_url"] = self.base_url or "http://localhost:11434/v1"
                client_kwargs["api_key"] = "ollama"  # Ollama requires a placeholder
            else:
                # Other providers require API key
                if not self.api_key:
                    logger.warning(f"No API key provided for {self.provider}. LLM features disabled.")
                    return
                client_kwargs["api_key"] = self.api_key
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
            
            try:
                self._client = OpenAI(**client_kwargs)
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
        context_type: str = "compile",
        api_context: Optional[str] = None,
        similar_examples: Optional[List[str]] = None,
        test_data_info: Optional[str] = None,
        family_config: Optional[Dict[str, Any]] = None,
        scaffolding_hints: Optional[List[str]] = None,
        section_heading: Optional[str] = None,
        description_context: Optional[str] = None,
        topic: Optional[str] = None,
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

        Returns:
            LLMResponse with fixed code
        """
        if context_type == "runtime":
            return self._fix_runtime_code(
                code, error_logs, api_context, similar_examples, test_data_info,
                family_config, scaffolding_hints, section_heading, description_context, topic
            )
        else:
            return self._fix_compile_code(
                code, error_logs, api_context, similar_examples, family_config,
                scaffolding_hints, section_heading, description_context, topic
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

        prompt_parts.extend([
            "",
            "## Original Code:",
            "```csharp",
            code,
            "```",
            "",
            "## Compilation Errors:",
            "```",
            error_logs,
            "```",
        ])

        # Add scaffolding hints if available
        if scaffolding_hints:
            prompt_parts.extend([
                "",
                "## Fix Hints (apply these minimal changes):",
            ])
            for hint in scaffolding_hints:
                prompt_parts.append(f"- {hint}")

        # Add few-shot examples
        prompt_parts.extend([
            "",
            "## Minimal Fix Patterns:",
            self.FEW_SHOT_EXAMPLES,
        ])

        # Add API patterns from config
        api_patterns = self._get_api_patterns(family_config)
        if api_patterns:
            prompt_parts.extend([
                "",
                "## API Usage Patterns (use these as reference):",
                api_patterns,
            ])

        if api_context:
            prompt_parts.extend([
                "",
                "## Relevant API Documentation:",
                api_context,
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
        )

        # Clean up response - remove markdown code blocks if present
        if response.success and response.content:
            response.content = self._clean_code_response(response.content)

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

        prompt_parts.extend([
            "",
            "## Code:",
            "```csharp",
            code,
            "```",
            "",
            "## Runtime Error:",
            "```",
            error_logs,
            "```",
        ])

        if test_data_info:
            prompt_parts.extend([
                "",
                "## Available Test Data Files:",
                test_data_info,
                "",
                "IMPORTANT: Update file paths to use these available files. Make minimal path changes.",
            ])

        if api_context:
            prompt_parts.extend([
                "",
                "## Relevant API Documentation:",
                api_context,
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
        )

        # Clean up response - remove markdown code blocks if present
        if response.success and response.content:
            response.content = self._clean_code_response(response.content)

        return response
    
    def _validate_code_response(self, content: str) -> bool:
        """
        Basic validation that LLM response looks like actual C# code.

        This prevents accepting prose explanations or malformed responses
        as valid code fixes.

        Args:
            content: The cleaned response content

        Returns:
            True if content appears to be valid C# code
        """
        if not content or not content.strip():
            return False

        content = content.strip()

        # Must contain at least some code indicators
        code_indicators = [
            'using ', 'class ', 'void ', 'public ', 'private ',
            'static ', 'new ', '(', ')', '{', '}', ';',
            'var ', 'string ', 'int ', 'bool ', 'return ',
        ]
        indicator_count = sum(1 for ind in code_indicators if ind in content)

        # Require at least 2 code indicators to be considered code
        if indicator_count < 2:
            return False

        # Reject if it looks like prose (starts with common explanation patterns)
        prose_patterns = [
            'I ', "I'm ", 'The ', 'This ', 'Here ', 'To ', 'You ',
            'Sorry', 'Unfortunately', 'Note:', 'Note that',
        ]
        first_word = content.split()[0] if content.split() else ""
        if any(content.startswith(p) for p in prose_patterns):
            return False

        return True

    def _clean_code_response(self, content: str) -> str:
        """Remove markdown code blocks from LLM response and validate."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```csharp or ```)
            if lines:
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        # Validate that the response looks like code
        if not self._validate_code_response(content):
            # Return empty string to trigger retry
            return ""

        return content
    
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

    def review_markdown_structured(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
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
            return self._review_with_instructor(markdown_content, code_snippets)
        else:
            logger.warning("Instructor not available, falling back to manual JSON parsing")
            return self._review_with_manual_parsing(markdown_content, code_snippets)

    def _review_with_instructor(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Review using Instructor for guaranteed schema compliance.

        This method uses Pydantic models to enforce the response schema,
        with automatic retries on validation failure.
        """
        system_prompt = """You are a technical documentation reviewer specializing in code example quality.

Your task is to verify code snippets in markdown documentation are:
1. Syntactically correct and complete
2. Relevant to the surrounding documentation context
3. Properly formatted with correct language tags
4. Free from security concerns or anti-patterns

Issue type definitions:
- syntax_error: Code has syntax errors or won't compile
- missing_context: Code is missing necessary setup or context
- incomplete_code: Code snippet is truncated or incomplete
- api_mismatch: Code uses deprecated or incorrect API calls
- security_concern: Code has potential security issues
- formatting_issue: Code formatting or language tag is wrong
- documentation_gap: Code doesn't match what documentation describes
- other: Other issues not in categories above

Severity definitions:
- info: Minor observation, not blocking
- warning: Should be addressed but not critical
- error: Must be fixed before publishing
- critical: Severe issue requiring immediate attention

ONLY report actual issues. If the code is fine, set approved=true with empty issues list."""

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
        prompt_parts.append("Review these snippets and provide your assessment:")

        try:
            # Wrap client with Instructor for structured outputs
            client = instructor.from_openai(self._client)

            # Make the request with automatic schema enforcement
            response = client.chat.completions.create(
                model=self.model,
                response_model=ReviewResponse,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "\n".join(prompt_parts)},
                ],
                max_retries=3,  # Automatic retry on validation failure
                temperature=0,  # Deterministic for consistency
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

            return {
                'approved': response.approved,
                'issues': processed_issues,
                'raw_response': response.model_dump_json(),
                'confidence': 'high',  # Instructor guarantees valid response
            }

        except Exception as e:
            logger.warning(f"Instructor-based review failed: {e}, falling back to manual parsing")
            # Fall back to manual parsing on error
            return self._review_with_manual_parsing(markdown_content, code_snippets)

    def _review_with_manual_parsing(
        self,
        markdown_content: str,
        code_snippets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Fallback review method with manual JSON parsing.

        Used when Instructor is unavailable or fails.
        """
        system_prompt = """You are a technical documentation reviewer specializing in code example quality.

Your task is to verify code snippets in markdown documentation are:
1. Syntactically correct and complete
2. Relevant to the surrounding documentation context
3. Properly formatted with correct language tags
4. Free from security concerns or anti-patterns

Return a JSON object with the following structure:
{
    "approved": true/false,
    "issues": [
        {
            "snippet_index": 0,
            "issue_type": "syntax_error|missing_context|incomplete_code|api_mismatch|security_concern|formatting_issue|documentation_gap|other",
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
            'confidence': 'low',  # Manual parsing has lower confidence
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
            result['confidence'] = 'medium'  # Successfully parsed

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

    def final_review(
        self,
        original_code: str,
        fixed_code: str,
    ) -> Dict[str, Any]:
        """
        Review fixed code to verify it preserves the original intent.

        This is Stage 5.5 in the pipeline - after code compiles successfully,
        verify that LLM fixes didn't change the functionality.

        Args:
            original_code: The original code (intent source)
            fixed_code: The code after LLM fixes

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

Return ONLY valid JSON, no markdown formatting."""

        prompt = f"""Analyze whether the FIXED CODE preserves the intent of the ORIGINAL CODE.

## ORIGINAL CODE (intent source):
```csharp
{original_code}
```

## FIXED CODE (after LLM fixes):
```csharp
{fixed_code}
```

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
