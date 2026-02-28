"""Service for generating README.md content for GitHub gists.

Uses the existing LLM service for intelligent generation with a
deterministic template fallback when LLM is unavailable or fails.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class GistReadmeService:
    """Generates README.md content for GitHub gists.

    Uses an LLM service to produce contextual documentation from code,
    falling back to a deterministic template on failure.
    """

    def __init__(self, llm_service, family: str = ""):
        """Initialize the gist readme service.

        Args:
            llm_service: An LLMService instance with a complete() method.
                         Accepted as a parameter to avoid circular imports.
            family: Default Aspose product family (e.g. "ZIP", "Words").
        """
        self.llm_service = llm_service
        self.family = family

    def generate_readme(
        self,
        code: str,
        example_key: str,
        family: str,
        file_path: str,
        description: str = "",
    ) -> str:
        """Generate README.md content for a gist.

        Calls the LLM service to produce a concise README based on the
        provided code snippet. Falls back to a deterministic template
        if the LLM call fails for any reason.

        Args:
            code: The C# source code for the example.
            example_key: Unique identifier for the example.
            family: Aspose product family (e.g. "ZIP", "Words").
            file_path: Original file path of the example source.
            description: Optional human-readable description of the example.

        Returns:
            Markdown string suitable for use as a README.md.
        """
        try:
            system_prompt = (
                f"You are a documentation specialist for {family} C# code examples."
            )

            code_snippet = code[:1500]

            user_prompt = (
                f"Write a concise README.md for a GitHub gist containing this "
                f"Aspose.{family} C# code example.\n\n"
                f"Example key: {example_key}\n"
                f"Source file: {file_path}\n"
            )
            if description:
                user_prompt += f"Description: {description}\n"
            user_prompt += (
                f"\nCode:\n```csharp\n{code_snippet}\n```\n\n"
                f"Include the following sections:\n"
                f"- Title (use the example key as a basis)\n"
                f"- Overview (brief description of what the code does)\n"
                f"- Usage (how to run or integrate the code)\n"
                f"- Prerequisites (required packages, runtime, license)\n\n"
                f"Keep it concise and factual. Do not include external links."
            )

            response = self.llm_service.complete(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.3,
            )

            readme = response.content
            readme = self._strip_links(readme)
            return readme

        except Exception as exc:
            logger.warning(
                "LLM readme generation failed for %s, using fallback template: %s",
                example_key,
                exc,
            )
            return self._fallback_readme(code, example_key, family)

    def _strip_links(self, md: str) -> str:
        """Remove markdown links, keeping their display text.

        Converts ``[text](url)`` to just ``text``, but preserves
        mailto: links unchanged.

        Args:
            md: Markdown string potentially containing links.

        Returns:
            Markdown string with non-mailto links replaced by their text.
        """
        # Match [text](url) but skip mailto: links
        return re.sub(r"\[([^\]]+)\]\((?!mailto:)[^\)]+\)", r"\1", md)

    def _fallback_readme(self, code: str, example_key: str, family: str) -> str:
        """Return a deterministic README template.

        Used when the LLM service is unavailable or returns an error.

        Args:
            code: The C# source code (unused in template but kept for
                  interface consistency).
            example_key: Unique identifier for the example.
            family: Aspose product family (e.g. "ZIP", "Words").

        Returns:
            A static markdown README string.
        """
        return (
            f"# {example_key}\n"
            f"\n"
            f"Example code for Aspose.{family}.\n"
            f"\n"
            f"## Overview\n"
            f"\n"
            f"This code demonstrates how to use Aspose.{family} in C#.\n"
            f"\n"
            f"## Usage\n"
            f"\n"
            f"1. Install the Aspose.{family} NuGet package\n"
            f"2. Set your metered license key\n"
            f"3. Run the code\n"
            f"\n"
            f"## Prerequisites\n"
            f"\n"
            f"- .NET 6.0 or later\n"
            f"- Aspose.{family} NuGet package\n"
            f"- Valid Aspose license\n"
            f"\n"
            f"## License\n"
            f"\n"
            f"This code is provided under the Aspose license terms.\n"
        )
