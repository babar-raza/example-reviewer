"""
Error Complexity Classifier for Smart Model Routing.

This module implements error complexity scoring for intelligent model routing:
- Simple errors (0.0-0.4) -> Small models (cost-optimized)
- Medium complexity (0.4-0.7) -> Medium models (balanced)
- Complex errors (0.7-1.0) -> Large models (capability-required)

Expected cost savings: 60-70% by routing simple errors to smaller models.
"""

import re
import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorComplexity(str, Enum):
    """Error complexity tiers for model routing."""
    SIMPLE = "simple"      # 0.0-0.4
    MEDIUM = "medium"      # 0.4-0.7
    COMPLEX = "complex"    # 0.7-1.0


class ErrorComplexityClassifier:
    """
    Score error complexity to route to appropriate model size.

    Strategy:
    1. Base score by error category (0.2-0.9)
    2. Apply modifiers for context (retries, error count, domain entities)
    3. Route to model tier based on final score
    """

    # Base complexity scores by error category
    CATEGORY_BASE_SCORES = {
        # Simple: Just add a line or fix obvious mistake
        'missing_type': 0.2,              # CS0246: Add using directive
        'undefined_variable': 0.3,        # CS0103: Variable name typo or missing definition
        'missing_namespace': 0.25,        # CS0246: Namespace variant

        # Medium: Requires some API knowledge or type inference
        'missing_argument': 0.45,         # CS7036: Need to infer correct argument
        'type_mismatch': 0.5,             # CS0029: Need type conversion understanding
        'missing_semicolon': 0.2,         # CS1002: Syntax fix
        'missing_brace': 0.2,             # CS1513: Syntax fix

        # Complex: Requires understanding method/class semantics
        'member_not_found': 0.75,         # CS1061: Needs API knowledge
        'ambiguous_reference': 0.75,      # CS0104: Namespace/type resolution
        'runtime_exception': 0.85,        # System.* exceptions need domain context
        'io_exception': 0.75,             # File/directory issues
        'null_reference': 0.7,            # NullReferenceException logic fix

        # Unknown/Uncertain: Use medium model
        'unknown': 0.55,
    }

    # Error code to category mapping
    ERROR_CODE_TO_CATEGORY = {
        'CS0103': 'undefined_variable',
        'CS0246': 'missing_type',
        'CS0029': 'type_mismatch',
        'CS1002': 'missing_semicolon',
        'CS1513': 'missing_brace',
        'CS1061': 'member_not_found',
        'CS0104': 'ambiguous_reference',
        'CS7036': 'missing_argument',
        'CS0117': 'member_not_found',
    }

    # Domain-specific keywords that require Aspose API knowledge
    DOMAIN_ENTITY_PATTERNS = [
        r'Aspose\.\w+',
        r'Archive\(',
        r'RarArchive',
        r'SevenZipArchive',
        r'CompressionLevel',
        r'CompressionMethod',
        r'EncryptionSettings',
        r'DeflateCompressionSettings',
        r'BZip2CompressionSettings',
        r'ChartType',
        r'DocumentBuilder',
        r'Watermark',
    ]

    def __init__(self):
        """Initialize the error complexity classifier."""
        self.error_code_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DOMAIN_ENTITY_PATTERNS
        ]

    def score_error(
        self,
        error_code: str,
        error_message: str,
        context: Optional[Dict] = None,
    ) -> float:
        """
        Return complexity score 0.0-1.0 (higher = more complex).

        Args:
            error_code: Error code (e.g., 'CS0246', 'CS0103')
            error_message: Full error message
            context: Optional context dict with keys:
                - retry_count: Number of previous fix attempts (0 by default)
                - all_errors: List of all errors in current attempt
                - error_history: List of previous error codes tried

        Returns:
            Complexity score between 0.0 and 1.0
        """
        if context is None:
            context = {}

        # Step 1: Get base score by category
        category = self._categorize_error(error_code)
        base_score = self.CATEGORY_BASE_SCORES.get(category, 0.55)

        # Step 2: Apply modifiers
        # Modifier 1: Retry count (previous attempts failed = escalate)
        retry_count = context.get('retry_count', 0)
        if retry_count > 0:
            base_score += 0.1 * min(retry_count, 2)  # Max +0.2 from retries

        # Modifier 2: Multiple errors = more complex
        all_errors = context.get('all_errors', [])
        error_count = len(all_errors)
        if error_count > 1:
            # Escalate for multiple errors (compound complexity)
            base_score += min(0.15, 0.05 * (error_count - 1))

        # Modifier 3: Domain entities = requires API knowledge
        if self._has_domain_entities(error_message):
            base_score += 0.1

        # Modifier 4: Cryptic error messages = harder to fix
        if self._is_cryptic_message(error_message):
            base_score += 0.08

        # Modifier 5: Error history suggests difficult issue
        error_history = context.get('error_history', [])
        if len(error_history) > 2:
            # Multiple different errors = complex problem
            base_score += 0.05

        # Clamp to [0.0, 1.0]
        final_score = min(1.0, max(0.0, base_score))

        logger.debug(
            f"Error complexity: code={error_code}, category={category}, "
            f"base={base_score:.2f}, final={final_score:.2f}, "
            f"retries={retry_count}, errors={error_count}"
        )

        return final_score

    def route_to_tier(self, score: float) -> str:
        """
        Map complexity score to model tier.

        Args:
            score: Complexity score (0.0-1.0)

        Returns:
            Model tier: 'small', 'medium', or 'large'
        """
        if score < 0.4:
            return "small"
        elif score < 0.7:
            return "medium"
        else:
            return "large"

    def get_complexity_level(self, score: float) -> ErrorComplexity:
        """
        Get complexity level enum from score.

        Args:
            score: Complexity score (0.0-1.0)

        Returns:
            ErrorComplexity enum value
        """
        if score < 0.4:
            return ErrorComplexity.SIMPLE
        elif score < 0.7:
            return ErrorComplexity.MEDIUM
        else:
            return ErrorComplexity.COMPLEX

    def _categorize_error(self, error_code: str) -> str:
        """
        Categorize error by error code.

        Mapping:
        - CS0246 -> missing_type
        - CS0103 -> undefined_variable
        - CS7036 -> missing_argument
        - CS1061 -> member_not_found
        - CS0104 -> ambiguous_reference
        - (Runtime exceptions handled separately)

        Args:
            error_code: Error code (e.g., 'CS0246')

        Returns:
            Category name from CATEGORY_BASE_SCORES keys
        """
        # Check exact matches first
        if error_code in self.ERROR_CODE_TO_CATEGORY:
            return self.ERROR_CODE_TO_CATEGORY[error_code]

        # Check if it's a runtime exception
        if self._is_runtime_exception(error_code):
            if any(keyword in error_code.upper() for keyword in ['EXCEPTION', 'ERROR']):
                # Try to classify the exception
                if any(keyword in error_code for keyword in [
                    'NullReferenceException',
                    'ArgumentNullException',
                ]):
                    return 'null_reference'
                elif any(keyword in error_code for keyword in [
                    'FileNotFoundException',
                    'DirectoryNotFoundException',
                    'IOException',
                ]):
                    return 'io_exception'
                else:
                    return 'runtime_exception'

        # Default to unknown
        return 'unknown'

    def _has_domain_entities(self, error_message: str) -> bool:
        """
        Check if error message mentions domain-specific types.

        Looks for Aspose.*, custom type names, archive-related classes.

        Args:
            error_message: Error message text

        Returns:
            True if domain entities detected
        """
        for pattern in self.error_code_patterns:
            if pattern.search(error_message):
                return True

        # Also check for specific Aspose patterns that might not match regex
        domain_keywords = [
            'CompressionLevel', 'EncryptionSettings', 'ArchiveEntry',
            'RarArchiveLoadOptions', 'SevenZipArchiveLoadOptions',
        ]
        for keyword in domain_keywords:
            if keyword in error_message:
                return True

        return False

    def _is_cryptic_message(self, error_message: str) -> bool:
        """
        Check if error message is cryptic/unclear.

        Cryptic messages are often stack traces or non-standard error formats.

        Args:
            error_message: Error message text

        Returns:
            True if message is cryptic
        """
        # Long, detailed messages suggest deeper issue
        if len(error_message) > 200:
            return True

        # Multiple lines suggest complex error
        if '\n' in error_message:
            return True

        # Certain patterns indicate complexity
        cryptic_patterns = [
            r'System\.',
            r'at\s+\w+\.',
            r'---.*---',
            r'\.\.\.',
        ]

        for pattern in cryptic_patterns:
            if re.search(pattern, error_message):
                return True

        return False

    def _is_runtime_exception(self, error_code: str) -> bool:
        """
        Check if error code is a runtime exception type.

        Args:
            error_code: Error code string

        Returns:
            True if it's a runtime exception
        """
        exception_keywords = [
            'Exception',
            'Error',
            'NullReference',
            'ArgumentNull',
            'FileNotFound',
            'IOException',
        ]

        return any(keyword in error_code for keyword in exception_keywords)

    def estimate_fix_difficulty(
        self,
        error_code: str,
        error_message: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, any]:
        """
        Estimate detailed fix difficulty metrics.

        Args:
            error_code: Error code
            error_message: Error message
            context: Optional context

        Returns:
            Dict with keys:
            - complexity_score: float (0.0-1.0)
            - complexity_level: str ('simple', 'medium', 'complex')
            - model_tier: str ('small', 'medium', 'large')
            - category: str (error category)
            - reasoning: str (human-readable explanation)
        """
        score = self.score_error(error_code, error_message, context)
        category = self._categorize_error(error_code)
        tier = self.route_to_tier(score)
        level = self.get_complexity_level(score)

        # Generate reasoning
        reasoning = self._generate_reasoning(category, score, context or {})

        return {
            'complexity_score': round(score, 3),
            'complexity_level': level.value,
            'model_tier': tier,
            'category': category,
            'reasoning': reasoning,
        }

    def _generate_reasoning(self, category: str, score: float, context: Dict) -> str:
        """
        Generate human-readable explanation of complexity score.

        Args:
            category: Error category
            score: Complexity score
            context: Context dict

        Returns:
            Reasoning string
        """
        category_descriptions = {
            'missing_type': 'Missing type - simple using directive fix',
            'undefined_variable': 'Undefined variable - likely typo or simple definition',
            'missing_namespace': 'Missing namespace - add using statement',
            'missing_argument': 'Missing argument - requires understanding method signature',
            'type_mismatch': 'Type mismatch - may need explicit conversion',
            'missing_semicolon': 'Syntax error - simple semicolon fix',
            'missing_brace': 'Syntax error - simple brace fix',
            'member_not_found': 'Member not found - requires API knowledge',
            'ambiguous_reference': 'Ambiguous reference - complex namespace resolution',
            'runtime_exception': 'Runtime exception - requires logic understanding',
            'io_exception': 'I/O exception - file system dependent',
            'null_reference': 'Null reference - data flow analysis needed',
            'unknown': 'Unknown error - uncertain classification',
        }

        base_reason = category_descriptions.get(category, 'Unknown error type')

        # Add context modifiers
        modifiers = []
        if context.get('retry_count', 0) > 0:
            modifiers.append(f"retry #{context['retry_count']}")
        if len(context.get('all_errors', [])) > 1:
            modifiers.append(f"{len(context['all_errors'])} errors total")
        if score >= 0.7:
            modifiers.append("high complexity")

        if modifiers:
            return f"{base_reason}; {', '.join(modifiers)}"
        return base_reason
