"""
Pattern Registry for Example Review System.
Loads and applies pattern-based fixes from family configurations.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """Represents a matched pattern in code."""
    pattern_name: str
    description: str
    match_text: str
    start_pos: int
    end_pos: int
    severity: str  # 'info', 'warning', 'error'


@dataclass
class FixResult:
    """Result of applying a fix."""
    pattern_name: str
    description: str
    applied: bool
    original_code: str
    fixed_code: str


class PatternRegistry:
    """
    Registry for code patterns and their fixes.
    Loads patterns from family configuration files.
    """

    def __init__(self, family_config_path: Path):
        """
        Initialize pattern registry.

        Args:
            family_config_path: Path to family configuration JSON file
        """
        self.family_config_path = family_config_path
        self.patterns: List[Dict] = []
        self.family_name = ""
        self.non_existent_apis: List[str] = []

        self._load_config()

    def _load_config(self):
        """Load family configuration from JSON file."""
        if not self.family_config_path.exists():
            raise FileNotFoundError(f"Family config not found: {self.family_config_path}")

        with open(self.family_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.family_name = config.get('family', '')
        self.patterns = config.get('patterns', [])
        self.non_existent_apis = config.get('non_existent_apis', [])

    def detect_issues(self, code: str) -> List[PatternMatch]:
        """
        Detect all pattern matches in code.

        Args:
            code: Source code to analyze

        Returns:
            List of pattern matches
        """
        matches = []

        for pattern in self.patterns:
            pattern_name = pattern.get('name')
            description = pattern.get('description', '')
            severity = pattern.get('severity', 'error')
            detection = pattern.get('detection', {})

            regex_pattern = detection.get('regex')
            if not regex_pattern:
                continue

            # Get regex flags
            flags = 0
            flag_names = detection.get('flags', [])
            if 'MULTILINE' in flag_names:
                flags |= re.MULTILINE
            if 'DOTALL' in flag_names:
                flags |= re.DOTALL
            if 'IGNORECASE' in flag_names:
                flags |= re.IGNORECASE

            # Find all matches
            try:
                regex = re.compile(regex_pattern, flags)
                for match in regex.finditer(code):
                    matches.append(PatternMatch(
                        pattern_name=pattern_name,
                        description=description,
                        match_text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end(),
                        severity=severity
                    ))
            except re.error as e:
                print(f"[!] Invalid regex in pattern '{pattern_name}': {e}")

        return matches

    def apply_fixes(self, code: str, auto_only: bool = True) -> Tuple[str, List[FixResult]]:
        """
        Apply pattern fixes to code.

        Args:
            code: Source code to fix
            auto_only: Only apply fixes with auto_apply=true

        Returns:
            Tuple of (fixed_code, list of fix results)
        """
        fixed_code = code
        fixes_applied = []

        for pattern in self.patterns:
            pattern_name = pattern.get('name')
            description = pattern.get('description', '')
            fix_config = pattern.get('fix', {})
            auto_apply = fix_config.get('auto_apply', False)

            # Skip if not auto-apply and we're only doing auto fixes
            if auto_only and not auto_apply:
                continue

            fix_type = fix_config.get('type')

            if fix_type == 'regex_replace':
                # Apply regex replacement
                detection = pattern.get('detection', {})
                regex_pattern = detection.get('regex')
                replacement = fix_config.get('replacement', '')

                if not regex_pattern:
                    continue

                # Get regex flags
                flags = 0
                flag_names = detection.get('flags', [])
                if 'MULTILINE' in flag_names:
                    flags |= re.MULTILINE
                if 'DOTALL' in flag_names:
                    flags |= re.DOTALL
                if 'IGNORECASE' in flag_names:
                    flags |= re.IGNORECASE

                try:
                    regex = re.compile(regex_pattern, flags)
                    if regex.search(fixed_code):
                        original = fixed_code
                        fixed_code = regex.sub(replacement, fixed_code)

                        if fixed_code != original:
                            fixes_applied.append(FixResult(
                                pattern_name=pattern_name,
                                description=description,
                                applied=True,
                                original_code=original,
                                fixed_code=fixed_code
                            ))
                except re.error as e:
                    print(f"[!] Invalid regex in pattern '{pattern_name}': {e}")

            elif fix_type == 'manual':
                # Manual fix - just detect, don't apply
                suggestion = fix_config.get('suggestion', '')
                fixes_applied.append(FixResult(
                    pattern_name=pattern_name,
                    description=f"{description}. Suggestion: {suggestion}",
                    applied=False,
                    original_code=code,
                    fixed_code=code
                ))

            elif fix_type == 'suggestion':
                # Suggestion only - don't apply
                suggestion = fix_config.get('suggestion', '')
                fixes_applied.append(FixResult(
                    pattern_name=pattern_name,
                    description=f"{description}. Suggestion: {suggestion}",
                    applied=False,
                    original_code=code,
                    fixed_code=code
                ))

        return fixed_code, fixes_applied

    def get_non_existent_apis(self) -> List[str]:
        """Get list of non-existent APIs for this family."""
        return self.non_existent_apis.copy()

    def get_pattern_count(self) -> int:
        """Get number of patterns loaded."""
        return len(self.patterns)

    def get_auto_fix_patterns(self) -> List[str]:
        """Get list of pattern names that have auto-fix enabled."""
        return [
            p.get('name')
            for p in self.patterns
            if p.get('fix', {}).get('auto_apply', False)
        ]
