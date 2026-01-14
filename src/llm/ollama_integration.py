"""
Ollama Integration for Example Review System.
Provides local LLM-based code fixing using Ollama.
"""

import re
import requests
from typing import Optional, List, Dict
from pathlib import Path


class OllamaClient:
    """Client for interacting with local Ollama service."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API
        """
        self.base_url = base_url
        self.selected_model: Optional[str] = None

    def select_model(self) -> Optional[str]:
        """
        Auto-select best available code model.

        Priority order:
        1. qwen2.5-coder
        2. deepseek-coder
        3. codellama
        4. llama3.1 (fallback)

        Returns:
            Selected model name or None
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()

            available_models = [m['name'] for m in data.get('models', [])]

            # Priority list
            preferred = [
                'qwen2.5-coder',
                'deepseek-coder',
                'codellama',
                'llama3.1',
                'llama3',
                'mistral'
            ]

            for pref in preferred:
                for model in available_models:
                    if pref in model.lower():
                        self.selected_model = model
                        return model

            # Fallback to first available
            if available_models:
                self.selected_model = available_models[0]
                return available_models[0]

            return None

        except Exception as e:
            print(f"[!] Failed to connect to Ollama: {e}")
            return None

    def get_available_models(self) -> List[str]:
        """
        Get list of available models in priority order.

        Returns models that are actually installed in Ollama,
        ordered by preference for code fixing tasks.

        Returns:
            List of model names in priority order, empty list if unavailable
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()

            available_models = [m['name'] for m in data.get('models', [])]

            # Priority list for code fixing
            preferred = [
                'qwen2.5-coder',
                'deepseek-coder',
                'codellama',
                'llama3.1',
                'llama3',
                'mistral'
            ]

            # Build ordered list of available models
            ordered = []
            for pref in preferred:
                for model in available_models:
                    if pref in model.lower() and model not in ordered:
                        ordered.append(model)

            # Add any remaining models not in priority list
            for model in available_models:
                if model not in ordered:
                    ordered.append(model)

            return ordered

        except Exception as e:
            print(f"[!] Failed to get available models: {e}")
            return []

    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.1) -> Optional[str]:
        """
        Generate response from Ollama.

        Args:
            prompt: Prompt text
            model: Model name (uses selected if None)
            temperature: Temperature for generation (0.1 for consistency)

        Returns:
            Generated text or None on failure
        """
        if model is None:
            model = self.selected_model

        if model is None:
            print("[!] No model selected")
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "max_tokens": 4096
                    }
                },
                timeout=120
            )

            response.raise_for_status()
            return response.json().get("response", "")

        except Exception as e:
            print(f"[!] Ollama generation failed: {e}")
            return None

    def fix_code(self, code: str, errors: str, family_config: Dict, attempt: int = 1) -> Optional[str]:
        """
        Fix code using LLM.

        Args:
            code: Code to fix
            errors: Compilation errors
            family_config: Family configuration dictionary
            attempt: Attempt number (1-3)

        Returns:
            Fixed code or None
        """
        if self.selected_model is None:
            self.select_model()

        if self.selected_model is None:
            return None

        # Build prompt
        prompt = self._build_fix_prompt(code, errors, family_config, attempt)

        # Generate fix
        response = self.generate(prompt, temperature=0.1)

        if not response:
            return None

        # Parse fixed code from response
        fixed_code = self._parse_code_from_response(response)

        return fixed_code

    def fix_code_with_model(
        self,
        code: str,
        errors: str,
        family_config: Dict,
        model: str,
        attempt: int = 1,
        api_context = None
    ) -> Optional[str]:
        """
        Fix code using a specific model.

        This method allows explicit model selection for model fallback strategies.
        Unlike fix_code(), this method does NOT auto-select a model.

        Args:
            code: Code to fix
            errors: Compilation errors
            family_config: Family configuration dictionary
            model: Specific model name to use
            attempt: Attempt number (1+)
            api_context: Optional API context for enriched prompting

        Returns:
            Fixed code or None
        """
        if not model:
            print("[!] No model specified for fix_code_with_model")
            return None

        # Build prompt with attempt-aware strictness and API context
        prompt = self._build_fix_prompt(code, errors, family_config, attempt, api_context)

        # Generate fix with specified model
        response = self.generate(prompt, model=model, temperature=0.1)

        if not response:
            return None

        # Parse fixed code from response
        fixed_code = self._parse_code_from_response(response)

        return fixed_code

    def _build_fix_prompt(self, code: str, errors: str, family_config: Dict, attempt: int, api_context = None) -> str:
        """Build prompt for code fixing with optional API context enrichment."""

        family_name = family_config.get('display_name', family_config.get('family', ''))
        nuget_package = family_config.get('nuget_config', {}).get('primary_package', {}).get('name', '')
        non_existent_apis = family_config.get('non_existent_apis', [])
        ollama_context = family_config.get('ollama_context', {})
        common_usings = ollama_context.get('common_usings', [])

        # Format non-existent APIs
        non_existent_list = '\n   '.join([f"- {api}" for api in non_existent_apis])

        # Format common usings
        usings_list = '\n   '.join(common_usings)

        # Format API reference context if available
        api_reference_section = ""
        if api_context:
            api_reference_section = api_context.to_prompt_text()

        # Format API patterns
        api_patterns_section = ""
        api_patterns = family_config.get('api_patterns', {})
        if api_patterns:
            api_patterns_section = "\n**COMMON PATTERNS:**\n"
            for pattern_name, pattern_info in api_patterns.items():
                api_patterns_section += f"\n{pattern_info['description']}:\n```csharp\n{pattern_info['code']}\n```\n"

        # Adjust prompt based on attempt (supports unlimited iterations)
        if attempt == 1:
            strictness = "Fix ONLY the compilation errors listed below."
        elif attempt == 2:
            strictness = "The previous fix attempt failed. Be more careful to use ONLY existing APIs. Fix ONLY the compilation errors."
        elif attempt == 3:
            strictness = "This is attempt 3. You MUST use ONLY the APIs that exist in the library. Do NOT hallucinate methods."
        elif attempt <= 6:
            strictness = f"Attempt {attempt}. Previous fixes failed compilation. Double-check API names against the NON-EXISTENT list. Use ONLY real APIs from {nuget_package}."
        else:
            strictness = f"Attempt {attempt}/{10}. This code has failed many times. Try a COMPLETELY DIFFERENT approach. Check EVERY method call against the library documentation. Do NOT guess."

        prompt = f"""You are a C# code fixer for {family_name} library (NuGet: {nuget_package}).

**YOUR TASK:** {strictness}

**COMPILATION ERRORS:**
{errors}

**CRITICAL: The following methods/APIs do NOT EXIST in this library:**
{non_existent_list}

**DO NOT use ANY of the above APIs. They will cause compilation errors.**
{api_reference_section}
{api_patterns_section}
**Common imports for this library:**
{usings_list}

**CODE TO FIX:**
```csharp
{code}
```

**INSTRUCTIONS:**
1. Fix ONLY the compilation errors listed above
2. Use ONLY the API signatures provided in the API REFERENCE section above
3. Preserve the original logic and structure
4. Do NOT hallucinate methods from the NON-EXISTENT list
5. Do NOT add try-catch, logging, or error handling unless required for compilation
6. Do NOT add comments or explanations
7. Return ONLY the fixed code inside a single ```csharp code fence

**FIXED CODE:**
"""

        return prompt

    def _parse_code_from_response(self, response: str) -> Optional[str]:
        """
        Parse code from LLM response.

        Args:
            response: LLM response text

        Returns:
            Extracted code or None
        """
        # Find ```csharp ... ``` fence
        patterns = [
            r'```(?:csharp|c#)\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                fixed_code = matches[0].strip()

                # Safety checks
                if len(fixed_code) == 0:
                    continue
                if len(fixed_code) > 50000:  # Suspiciously large
                    continue

                return fixed_code

        return None

    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
