"""
ModelDiscoveryService for discovering available models from LLM endpoints.
Supports OpenAI-compatible /v1/models endpoints.
"""

import os
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class ModelDiscoveryService:
    """
    Discovers available models from OpenAI-compatible LLM endpoints.

    Supports multiple authentication methods and gracefully falls back
    if the endpoint is unreachable or authentication fails.
    """

    # Environment variable names to try for API authentication
    API_KEY_ENV_VARS = [
        "LLM_API_KEY",
        "LITELLM_KEY",
        "OPENAI_API_KEY",
    ]

    # Model name patterns for tier mapping
    TIER_PATTERNS = {
        "small": ["7b", "small", "mini"],
        "medium": ["13b", "medium"],
        "large": ["70b", "large", "xl"],
    }

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout_seconds: int = 10):
        """
        Initialize ModelDiscoveryService.

        Args:
            base_url: Base URL for LLM endpoint (e.g., https://llm.example.com/v1)
            api_key: API key for authentication. If None, tries environment variables.
            timeout_seconds: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._models = None
        self._tiers = None

        # Try to get API key from parameter or environment
        self.api_key = api_key
        if not self.api_key:
            self.api_key = self._get_api_key_from_env()

        if self.api_key:
            logger.debug(f"ModelDiscoveryService initialized with base_url: {self.base_url}")
        else:
            logger.warning(
                f"ModelDiscoveryService initialized without API key. "
                f"Tried environment variables: {', '.join(self.API_KEY_ENV_VARS)}"
            )

    @staticmethod
    def _get_api_key_from_env() -> Optional[str]:
        """
        Try multiple environment variable names for API key.

        Returns:
            API key if found, None otherwise.
        """
        for env_var in ModelDiscoveryService.API_KEY_ENV_VARS:
            api_key = os.getenv(env_var)
            if api_key:
                logger.debug(f"Found API key in environment variable: {env_var}")
                return api_key

        logger.debug(
            f"API key not found in environment variables: {', '.join(ModelDiscoveryService.API_KEY_ENV_VARS)}"
        )
        return None

    def discover_models(self, force_refresh: bool = False) -> List[Dict]:
        """
        Query /v1/models endpoint to discover available models.

        Results are cached after first successful call unless force_refresh is True.

        Args:
            force_refresh: If True, bypass cache and query endpoint again.

        Returns:
            List of model dictionaries from endpoint. Empty list if discovery fails.
            Each model dict typically contains at least: {'id': str, 'object': str}
        """
        if self._models is not None and not force_refresh:
            logger.debug(f"Returning cached models: {len(self._models)} models")
            return self._models

        if not self.api_key:
            logger.warning("Cannot discover models: no API key available")
            return []

        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            logger.debug(f"Querying models endpoint: {url}")
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 401:
                logger.warning(f"Model discovery: Authentication failed (401). Check API key.")
                return []
            elif response.status_code == 403:
                logger.warning(f"Model discovery: Access forbidden (403). API key may not have permission.")
                return []
            elif response.status_code == 404:
                logger.warning(f"Model discovery: Endpoint not found (404). Check base_url: {self.base_url}")
                return []
            elif response.status_code == 503:
                logger.warning(f"Model discovery: Service unavailable (503). Endpoint may be down.")
                return []

            response.raise_for_status()

            data = response.json()
            self._models = data.get("data", [])

            logger.info(f"Model discovery successful: found {len(self._models)} models")
            return self._models

        except requests.exceptions.Timeout:
            logger.warning(
                f"Model discovery: Request timeout after {self.timeout_seconds} seconds. "
                f"Endpoint may be slow or unreachable."
            )
            return []
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Model discovery: Connection failed. {str(e)}")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"Model discovery: HTTP request failed. {str(e)}")
            return []
        except (ValueError, KeyError) as e:
            logger.warning(f"Model discovery: Invalid response format. {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Model discovery: Unexpected error. {str(e)}")
            return []

    def map_to_tiers(self, models: Optional[List[Dict]] = None) -> Dict[str, str]:
        """
        Map discovered models to small/medium/large tiers based on model name patterns.

        Uses heuristic pattern matching on model IDs:
        - small: contains '7b' or 'small' or 'mini'
        - medium: contains '13b' or 'medium'
        - large: contains '70b' or 'large' or 'xl'

        If multiple models match a tier, returns the first one encountered.

        Args:
            models: List of model dicts. If None, uses discovered models.

        Returns:
            Dict mapping tier names to model IDs. May have 0-3 entries.
            Example: {'small': 'qwen2.5-coder:7b', 'large': 'qwen2.5:70b'}
        """
        if models is None:
            if self._models is None:
                models = self.discover_models()
            else:
                models = self._models

        tiers = {}

        for model in models:
            model_id = model.get("id", "").lower()

            # Check each tier pattern
            for tier_name, patterns in self.TIER_PATTERNS.items():
                # Skip if tier already assigned
                if tier_name in tiers:
                    continue

                # Check if any pattern matches
                for pattern in patterns:
                    if pattern in model_id:
                        tiers[tier_name] = model.get("id", "")
                        logger.debug(f"Mapped model {model.get('id')} to tier: {tier_name} (pattern: {pattern})")
                        break

        return tiers

    def get_best_model_for_tier(self, tier: str, models: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Get the best model ID for a specific tier.

        Args:
            tier: Tier name ('small', 'medium', or 'large')
            models: List of model dicts. If None, uses discovered models.

        Returns:
            Model ID for tier, or None if not found.
        """
        tiers = self.map_to_tiers(models)
        return tiers.get(tier)

    def validate_endpoint(self) -> bool:
        """
        Test connectivity and authentication to the endpoint.

        Returns:
            True if endpoint is reachable and authenticated, False otherwise.
        """
        if not self.api_key:
            logger.warning("Cannot validate endpoint: no API key available")
            return False

        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                logger.info(f"Endpoint validation successful: {self.base_url}")
                return True
            else:
                logger.warning(f"Endpoint validation failed with status {response.status_code}: {self.base_url}")
                return False

        except Exception as e:
            logger.warning(f"Endpoint validation failed: {str(e)}")
            return False

    def clear_cache(self):
        """Clear cached models and tier mappings."""
        self._models = None
        self._tiers = None
        logger.debug("Model discovery cache cleared")
