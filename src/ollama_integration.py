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

    def _build_fix_prompt(self, code: str, errors: str, family_config: Dict, attempt: int) -> str:
        """Build prompt for code fixing."""

        family_name = family_config.get('display_name', family_config.get('family', ''))
        nuget_package = family_config.get('nuget_config', {}).get('primary_package', {}).get('name', '')
        non_existent_apis = family_config.get('non_existent_apis', [])
        ollama_context = family_config.get('ollama_context', {})
        common_usings = ollama_context.get('common_usings', [])

        # Format non-existent APIs
        non_existent_list = '\n   '.join([f"- {api}" for api in non_existent_apis])

        # Format common usings
        usings_list = '\n   '.join(common_usings)

        # Adjust prompt based on attempt
        if attempt == 1:
            strictness = "Fix ONLY the compilation errors listed below."
        elif attempt == 2:
            strictness = "The previous fix attempt failed. Be more careful to use ONLY existing APIs. Fix ONLY the compilation errors."
        else:
            strictness = "This is the FINAL attempt. You MUST use ONLY the APIs that exist in the library. Do NOT hallucinate methods."

        prompt = f"""You are a C# code fixer for {family_name} library (NuGet: {nuget_package}).

**YOUR TASK:** {strictness}

**COMPILATION ERRORS:**
{errors}

**CRITICAL: The following methods/APIs do NOT EXIST in this library:**
{non_existent_list}

**DO NOT use ANY of the above APIs. They will cause compilation errors.**

**Common imports for this library:**
{usings_list}

**CODE TO FIX:**
```csharp
{code}
```

**INSTRUCTIONS:**
1. Fix ONLY the compilation errors listed above
2. Preserve the original logic and structure
3. Do NOT hallucinate methods from the NON-EXISTENT list
4. Do NOT add try-catch, logging, or error handling unless required for compilation
5. Do NOT add comments or explanations
6. Return ONLY the fixed code inside a single ```csharp code fence

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
