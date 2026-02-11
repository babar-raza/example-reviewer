"""
Escalation Reason Classifier for NEEDS_REVIEW Status (Phase-2 Task 2).

This module provides deterministic classification of why code examples
are escalated to NEEDS_REVIEW status using a controlled vocabulary.
"""

import re
from typing import Optional, List


class EscalationReason:
    """Controlled vocabulary for escalation reasons."""

    # Core reasons
    NO_CSHARP_CODE_BLOCK = "no_csharp_code_block"
    SNIPPET_TOO_INCOMPLETE = "snippet_too_incomplete"
    MISSING_REQUIRED_CONTEXT = "missing_required_context"
    AMBIGUOUS_INPUT_FILE = "ambiguous_input_file"
    REQUIRES_PRODUCT_SPECIFIC_SETUP = "requires_product_specific_setup"

    # Additional specific reasons
    EMPTY_CODE = "empty_code"
    ONLY_COMMENTS = "only_comments"
    NO_ASPOSE_USAGE = "no_aspose_usage"
    FRAGMENT_WITHOUT_METHOD = "fragment_without_method"
    MULTIPLE_CLASSES_OR_NAMESPACES = "multiple_classes_or_namespaces"

    # Phase-2: Infrastructure blockers (not code quality issues)
    INFRA_BLOCKED_RAR_FIXTURE = "missing_rar_fixture"
    INFRA_BLOCKED_7Z_FIXTURE = "missing_7z_fixture"
    INFRA_BLOCKED_PASSWORD = "requires_password_secret"
    INFRA_BLOCKED_FORMAT = "unsupported_archive_format"
    INFRA_BLOCKED_EXTERNAL = "external_dependency_missing"
    INFRA_MISSING_TEST_DATA = "missing_test_data"

    # Catch-all
    OTHER = "other"

    @classmethod
    def all_reasons(cls) -> List[str]:
        """Get all valid escalation reasons."""
        return [
            cls.NO_CSHARP_CODE_BLOCK,
            cls.SNIPPET_TOO_INCOMPLETE,
            cls.MISSING_REQUIRED_CONTEXT,
            cls.AMBIGUOUS_INPUT_FILE,
            cls.REQUIRES_PRODUCT_SPECIFIC_SETUP,
            cls.EMPTY_CODE,
            cls.ONLY_COMMENTS,
            cls.NO_ASPOSE_USAGE,
            cls.FRAGMENT_WITHOUT_METHOD,
            cls.MULTIPLE_CLASSES_OR_NAMESPACES,
            cls.INFRA_BLOCKED_RAR_FIXTURE,
            cls.INFRA_BLOCKED_7Z_FIXTURE,
            cls.INFRA_BLOCKED_PASSWORD,
            cls.INFRA_BLOCKED_FORMAT,
            cls.INFRA_BLOCKED_EXTERNAL,
            cls.INFRA_MISSING_TEST_DATA,
            cls.OTHER,
        ]

    @classmethod
    def is_infra_blocked(cls, reason: str) -> bool:
        """Check if an escalation reason is an infrastructure blocker."""
        infra_reasons = {
            cls.INFRA_BLOCKED_RAR_FIXTURE,
            cls.INFRA_BLOCKED_7Z_FIXTURE,
            cls.INFRA_BLOCKED_PASSWORD,
            cls.INFRA_BLOCKED_FORMAT,
            cls.INFRA_BLOCKED_EXTERNAL,
            cls.INFRA_MISSING_TEST_DATA,
        }
        return reason in infra_reasons

    @classmethod
    def is_precheck_only(cls, reason: str) -> bool:
        """Check if an escalation reason is a pre-check failure (empty/incomplete)."""
        precheck_reasons = {
            cls.EMPTY_CODE,
            cls.ONLY_COMMENTS,
            cls.NO_CSHARP_CODE_BLOCK,
            cls.SNIPPET_TOO_INCOMPLETE,
        }
        return reason in precheck_reasons


def classify_escalation_reason(
    code: str,
    language: str = "csharp",
    file_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """
    Classify the escalation reason for a code snippet.

    This function uses deterministic heuristics to determine why a code
    example should be escalated to NEEDS_REVIEW.

    Args:
        code: The code snippet to classify
        language: Programming language (default: csharp)
        file_path: Source file path (optional)
        error_message: Compilation/runtime error message (optional)

    Returns:
        Escalation reason from EscalationReason vocabulary
    """
    if not code or not code.strip():
        return EscalationReason.EMPTY_CODE

    code = code.strip()
    code_lower = code.lower()

    # Check 1: Language validation
    if language.lower() not in ["csharp", "c#", "cs"]:
        return EscalationReason.NO_CSHARP_CODE_BLOCK

    # Check 2: Only comments (no actual code)
    code_without_comments = _remove_comments(code)
    if not code_without_comments.strip():
        return EscalationReason.ONLY_COMMENTS

    # Check 3: Too short/incomplete (less than 3 lines of actual code)
    code_lines = [line for line in code_without_comments.split('\n') if line.strip()]
    if len(code_lines) < 3:
        return EscalationReason.SNIPPET_TOO_INCOMPLETE

    # Check 3b: Skeleton/placeholder code — only creates objects with placeholder comments
    placeholder_phrases = [
        "further processing", "your code here", "add your", "todo",
        "processing steps follow", "processing follows here",
    ]
    if any(phrase in code.lower() for phrase in placeholder_phrases):
        # Count actual code statements (excluding using/braces/comments)
        stmt_lines = [l for l in code_lines
                      if not l.startswith('using ') and not l.startswith('{') and not l.startswith('}')]
        if len(stmt_lines) <= 3:
            return EscalationReason.SNIPPET_TOO_INCOMPLETE

    # Check 4: No Aspose usage detected
    if not _has_aspose_usage(code):
        return EscalationReason.NO_ASPOSE_USAGE

    # Check 5: Requires product-specific setup (license, activation)
    if _requires_product_setup(code, error_message):
        return EscalationReason.REQUIRES_PRODUCT_SPECIFIC_SETUP

    # Check 6: Fragment without method or class structure
    if _is_fragment_without_structure(code):
        return EscalationReason.FRAGMENT_WITHOUT_METHOD

    # Check 7: Missing required context (external files, undefined variables)
    if _missing_required_context(code, error_message):
        return EscalationReason.MISSING_REQUIRED_CONTEXT

    # Check 8: Ambiguous input file references
    if _has_ambiguous_file_references(code):
        return EscalationReason.AMBIGUOUS_INPUT_FILE

    # Check 9: Multiple classes or namespaces (complex example)
    if _has_multiple_classes_or_namespaces(code):
        return EscalationReason.MULTIPLE_CLASSES_OR_NAMESPACES

    # Default: other
    return EscalationReason.OTHER


def _remove_comments(code: str) -> str:
    """Remove single-line and multi-line comments from C# code."""
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove single-line comments
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    return code


def _has_aspose_usage(code: str) -> bool:
    """Check if code contains Aspose API usage."""
    aspose_patterns = [
        r'using\s+Aspose\.',
        r'Aspose\.\w+',
        r'new\s+Archive\(',
        r'new\s+Zip\w+',
        r'License\(\)',
        r'SetLicense\(',
    ]

    for pattern in aspose_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return True

    return False


def _requires_product_setup(code: str, error_message: Optional[str] = None) -> bool:
    """Check if code requires product-specific setup (license, activation)."""
    setup_patterns = [
        r'License\(\)',
        r'SetLicense\(',
        r'license\.lic',
        r'Aspose\..*\.License',
    ]

    for pattern in setup_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return True

    if error_message:
        error_lower = error_message.lower()
        if any(keyword in error_lower for keyword in ['license', 'trial', 'activation']):
            return True

    return False


def _is_fragment_without_structure(code: str) -> bool:
    """Check if code is a fragment without method or class structure."""
    # Look for method or class declarations
    has_method = bool(re.search(r'\b(public|private|protected|internal|static)?\s*(void|int|string|bool|var|class|interface)\s+\w+\s*\(', code))
    has_class = bool(re.search(r'\bclass\s+\w+', code))
    has_namespace = bool(re.search(r'\bnamespace\s+\w+', code))
    has_main = bool(re.search(r'\bstatic\s+void\s+Main\s*\(', code))

    # If no structure indicators found, it's likely a fragment
    if not (has_method or has_class or has_namespace or has_main):
        # Check if it's just variable declarations and method calls (fragment)
        lines = code.split('\n')
        non_empty_lines = [l.strip() for l in lines if l.strip()]

        # If most lines are just statements (no declarations), it's a fragment
        statement_count = sum(1 for line in non_empty_lines if line.endswith(';'))
        if statement_count >= len(non_empty_lines) * 0.7:
            return True

    return False


def _missing_required_context(code: str, error_message: Optional[str] = None) -> bool:
    """Check if code is missing required external context."""
    if error_message:
        error_lower = error_message.lower()

        # Check for undefined variable/type errors
        if any(keyword in error_lower for keyword in [
            'does not exist',
            'not found',
            'undefined',
            'is not defined',
            'name does not exist in',
        ]):
            return True

        # Check for missing namespace errors
        if 'missing' in error_lower and 'directive' in error_lower:
            return False  # This is fixable with using statements

    # Check for variables used but not declared
    # This is a simple heuristic - might need refinement
    code_without_strings = re.sub(r'"[^"]*"', '', code)

    # Look for common patterns of external file dependencies
    external_file_patterns = [
        r'File\.ReadAllText\(',
        r'File\.ReadAllBytes\(',
        r'Directory\.GetFiles\(',
        r'Path\.Combine\(',
    ]

    for pattern in external_file_patterns:
        if re.search(pattern, code_without_strings):
            # If using external files but no file creation logic, might need context
            has_file_creation = bool(re.search(r'File\.WriteAllText\(|File\.WriteAllBytes\(|File\.Create\(', code))
            if not has_file_creation:
                return True

    return False


def _has_ambiguous_file_references(code: str) -> bool:
    """Check if code has ambiguous file path references."""
    # Look for file path strings that are placeholders or unclear
    placeholder_patterns = [
        r'["\']sample\.(zip|txt|pdf|doc)',
        r'["\']test\.(zip|txt|pdf|doc)',
        r'["\']input\.(zip|txt|pdf|doc)',
        r'["\']archive\.(zip|rar|7z)',
        r'["\']your',
        r'["\']path/to/',
        r'["\']<.*?>',
    ]

    for pattern in placeholder_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return True

    return False


def _has_multiple_classes_or_namespaces(code: str) -> bool:
    """Check if code has multiple classes or namespaces (complex example)."""
    # Count class declarations
    class_count = len(re.findall(r'\bclass\s+\w+', code))

    # Count namespace declarations
    namespace_count = len(re.findall(r'\bnamespace\s+\w+', code))

    # If multiple of either, it's a complex example
    return class_count > 1 or namespace_count > 1


def should_escalate_to_review(
    code: str,
    language: str = "csharp",
    file_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Determine if a code snippet should be escalated to NEEDS_REVIEW pre-compilation.

    Phase-2 Task 2: Conservative escalation - only auto-escalate pre-compilation
    for truly non-fixable cases. Other reasons are handled by wrapper + compile-fix
    + runtime selection, or escalated later with concrete evidence.

    Auto-escalate ONLY for:
        - empty_code
        - only_comments
        - no_csharp_code_block
        - snippet_too_incomplete (very short)

    Do NOT auto-escalate pre-compilation for (let wrapper/compiler handle):
        - fragment_without_method (wrapper can wrap fragments)
        - ambiguous_input_file (runtime selection can resolve)
        - missing_required_context (compile-fix can add context)
        - multiple_classes_or_namespaces (wrapper can handle)
        - no_aspose_usage (may be utility code, let compiler try)
        - requires_product_specific_setup (try compilation first)

    Args:
        code: The code snippet
        language: Programming language
        file_path: Source file path (optional)
        error_message: Error message (optional)

    Returns:
        Tuple of (should_escalate: bool, reason: str)
    """
    reason = classify_escalation_reason(code, language, file_path, error_message)

    # Phase-2: Only escalate for truly non-fixable pre-compilation cases
    # These are cases where no amount of wrapping or LLM fixing can help
    PRE_COMPILATION_FATAL_REASONS = {
        EscalationReason.EMPTY_CODE,
        EscalationReason.ONLY_COMMENTS,
        EscalationReason.NO_CSHARP_CODE_BLOCK,
        EscalationReason.SNIPPET_TOO_INCOMPLETE,
    }

    should_escalate = reason in PRE_COMPILATION_FATAL_REASONS

    return should_escalate, reason
