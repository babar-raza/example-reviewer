"""
Aspose.ZIP Example Fixer
Automatically fixes common issues in code examples and validates them
"""

import os
import re
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class FixApplied:
    """Represents a fix applied to code"""
    fix_type: str
    description: str
    line_number: Optional[int] = None

@dataclass
class ValidationResult:
    """Result of validating a code example"""
    success: bool
    original_code: str
    fixed_code: str
    fixes_applied: List[FixApplied]
    compilation_output: str
    error_messages: List[str]

class AsposeZipExampleFixer:
    """Fixes and validates Aspose.ZIP code examples"""

    def __init__(self, validator_project_path: str):
        self.validator_project_path = Path(validator_project_path)
        self.fix_stats = {
            'deflate_params_fixed': 0,
            'async_methods_fixed': 0,
            'stream_disposal_fixed': 0,
            'directory_compression_improved': 0
        }

    def fix_deflate_compression_settings(self, code: str) -> Tuple[str, List[FixApplied]]:
        """Fix DeflateCompressionSettings to not accept parameters"""
        fixes = []

        # Pattern 1: new DeflateCompressionSettings(CompressionLevel.*)
        pattern1 = r'new\s+DeflateCompressionSettings\s*\([^)]+\)'
        if re.search(pattern1, code):
            fixed_code = re.sub(pattern1, 'new DeflateCompressionSettings()', code)
            fixes.append(FixApplied(
                fix_type='deflate_params',
                description='Removed parameters from DeflateCompressionSettings() - it takes no parameters'
            ))
            self.fix_stats['deflate_params_fixed'] += 1
            return fixed_code, fixes

        return code, fixes

    def fix_async_methods(self, code: str) -> Tuple[str, List[FixApplied]]:
        """Fix non-existent async methods"""
        fixes = []
        fixed_code = code

        # SaveAsync -> Save
        if 'SaveAsync' in code:
            fixed_code = fixed_code.replace('await archive.SaveAsync(', 'archive.Save(')
            fixed_code = fixed_code.replace('.SaveAsync(', '.Save(')
            fixes.append(FixApplied(
                fix_type='async_methods',
                description='Replaced SaveAsync with Save - async methods are not available in Aspose.ZIP'
            ))
            self.fix_stats['async_methods_fixed'] += 1

        # Remove await if it's only used for SaveAsync
        if 'await' in fixed_code and 'SaveAsync' not in fixed_code:
            # Check if this is the only await
            await_count = fixed_code.count('await')
            if await_count == 1 and 'archive.Save(' in fixed_code:
                fixed_code = fixed_code.replace('await archive.Save(', 'archive.Save(')

        # Fix async method signatures if needed
        if 'async' in fixed_code and 'await' not in fixed_code:
            # Remove async keyword if no await is present
            fixed_code = re.sub(r'\basync\s+\(', '(', fixed_code)
            fixed_code = re.sub(r',\s*async\s+\(', ', (', fixed_code)

        return fixed_code, fixes

    def fix_stream_disposal_timing(self, code: str) -> Tuple[str, List[FixApplied]]:
        """
        Fix stream disposal timing issues.
        Streams should not be disposed before archive.Save() is called.
        """
        fixes = []

        # Check for the problematic pattern:
        # using (var ms = new MemoryStream(...)) { archive.CreateEntry(..., ms, ...); }
        # ... (ms is disposed here)
        # archive.Save(...)

        # This is complex to fix automatically without breaking other code
        # For now, we'll detect and warn rather than auto-fix
        pattern = r'using\s*\([^)]*\bStream[^)]*\)\s*\{[^}]*CreateEntry[^}]*\}[^{]*\.Save'

        if re.search(pattern, code, re.DOTALL):
            # Instead of auto-fixing, we'll add a comment warning
            fixes.append(FixApplied(
                fix_type='stream_disposal',
                description='WARNING: Stream may be disposed before Save() - ensure streams remain open until after archive.Save()'
            ))
            self.fix_stats['stream_disposal_fixed'] += 1

        return code, fixes

    def suggest_directory_compression(self, code: str) -> Tuple[str, List[FixApplied]]:
        """Suggest using CreateEntries for directory compression"""
        fixes = []

        # Look for manual directory iteration patterns
        has_directory_iteration = any([
            'Directory.GetFiles' in code,
            'Directory.EnumerateFiles' in code,
            'GetFiles' in code and 'SearchOption.AllDirectories' in code
        ])

        has_create_entry_loop = 'CreateEntry' in code and ('foreach' in code or 'for' in code)

        if has_directory_iteration and has_create_entry_loop:
            fixes.append(FixApplied(
                fix_type='directory_compression',
                description='SUGGESTION: Consider using archive.CreateEntries(directoryPath, includeRootDirectory) for entire directory compression'
            ))
            self.fix_stats['directory_compression_improved'] += 1

        return code, fixes

    def apply_all_fixes(self, code: str) -> Tuple[str, List[FixApplied]]:
        """Apply all available fixes to the code"""
        all_fixes = []

        # Fix 1: DeflateCompressionSettings parameters
        code, fixes = self.fix_deflate_compression_settings(code)
        all_fixes.extend(fixes)

        # Fix 2: Async methods
        code, fixes = self.fix_async_methods(code)
        all_fixes.extend(fixes)

        # Fix 3: Stream disposal (detection only)
        code, fixes = self.fix_stream_disposal_timing(code)
        all_fixes.extend(fixes)

        # Fix 4: Directory compression suggestion
        code, fixes = self.suggest_directory_compression(code)
        all_fixes.extend(fixes)

        return code, all_fixes

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate code using the C# validator.
        Returns (success, output)
        """
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cs', delete=False, encoding='utf-8') as f:
                temp_file = f.name
                f.write(code)

            # Run validator
            result = subprocess.run(
                ['dotnet', 'run', '--', 'validate-file', temp_file],
                cwd=str(self.validator_project_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass

            output = result.stdout + result.stderr
            success = 'COMPILATION SUCCESSFUL' in output

            return success, output

        except subprocess.TimeoutExpired:
            return False, "Validation timeout"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def fix_and_validate_example(self, code: str) -> ValidationResult:
        """
        Fix and validate a code example.
        Returns ValidationResult with all details.
        """
        original_code = code

        # Apply fixes
        fixed_code, fixes_applied = self.apply_all_fixes(code)

        # Validate fixed code
        success, compilation_output = self.validate_code(fixed_code)

        # Extract error messages if failed
        error_messages = []
        if not success:
            # Parse compilation errors
            for line in compilation_output.split('\n'):
                if 'error' in line.lower() or 'CS' in line:
                    error_messages.append(line.strip())

        return ValidationResult(
            success=success,
            original_code=original_code,
            fixed_code=fixed_code,
            fixes_applied=fixes_applied,
            compilation_output=compilation_output,
            error_messages=error_messages
        )

    def get_fix_stats(self) -> Dict:
        """Get statistics about fixes applied"""
        return self.fix_stats.copy()


def main():
    """Main entry point for testing"""
    script_dir = Path(__file__).parent.parent
    validator_path = script_dir / "test-examples"

    fixer = AsposeZipExampleFixer(str(validator_path))

    # Test with a sample code snippet
    test_code = """
using var archive = new Archive();
var deflate = new DeflateCompressionSettings(CompressionLevel.Normal);
var settings = new ArchiveEntrySettings(deflate);

using (var ms = new MemoryStream(Encoding.UTF8.GetBytes("test")))
{
    archive.CreateEntry("test.txt", ms, settings);
}

archive.Save("output.zip");
"""

    print("Testing Example Fixer")
    print("=" * 80)
    print("Original code:")
    print(test_code)
    print()

    result = fixer.fix_and_validate_example(test_code)

    print("Fixes applied:")
    for fix in result.fixes_applied:
        print(f"  - {fix.fix_type}: {fix.description}")
    print()

    print("Fixed code:")
    print(result.fixed_code)
    print()

    print(f"Validation: {'SUCCESS' if result.success else 'FAILED'}")
    if not result.success:
        print("Errors:")
        for error in result.error_messages:
            print(f"  - {error}")

    print()
    print("Fix Statistics:")
    for key, value in fixer.get_fix_stats().items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
