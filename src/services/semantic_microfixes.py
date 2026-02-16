"""
Semantic Micro-Fixes: Diagnostic-Driven Code Corrections

This module provides targeted, deterministic fixes for common compilation errors
based on compiler error codes. Each fix is safe, predictable, and limited to
specific allowlisted patterns.

Error Handlers:
- CS0103: Undefined Name (insert variable definitions)
- CS7036: Missing Argument (supply safe defaults)
- CS0246: Missing Using Directive (from allowlist)
"""

import re
import json
import difflib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


# Allowlist for CS0246: Type/Namespace -> Using Directive
# Base entries (fallback if catalog not available)
USING_DIRECTIVE_ALLOWLIST: Dict[str, str] = {
    "Archive": "using Aspose.Zip;",
    "SevenZipArchive": "using Aspose.Zip.SevenZip;",
    "RarArchive": "using Aspose.Zip.Rar;",
    "GzipArchive": "using Aspose.Zip.Gzip;",
    "TarArchive": "using Aspose.Zip.Tar;",
    # Common BCL types used alongside Aspose.Zip examples
    "CompressionLevel": "using System.IO.Compression;",
    "CompressionMode": "using System.IO.Compression;",
}

# NOTE: Module-level catalog loading removed in TASK-2A (multi-family refactor)
# Using directives are now loaded dynamically via FamilyServiceRegistry
# Base allowlist remains as fallback for backwards compatibility


# Allowlist for CS0103: Variable names that can be auto-defined
UNDECLARED_VAR_ALLOWLIST = {"outputPath", "destinationPath", "archivePath", "filePath", "dataDir", "baseDir", "sourceDir", "outputDir", "baseFolder", "SourceDir", "OutputDir", "outputFolder", "output"}


# Password normalization: common placeholder passwords to replace with test password
# Canonical test password is "p@s$" — matches ALL Aspose.ZIP official examples
# (DecryptRarArchive.cs, DecompressAESEncryptedStoredFile.cs, etc.)
PLACEHOLDER_PASSWORDS = ["your_password", "your-password", "mypassword", "my_password",
                         "secretpassword", "your_secret", "my_secret", "password"]
REAL_TEST_PASSWORD = "p@s$"


def fix_placeholder_passwords(code: str) -> Tuple[str, str]:
    """Replace common placeholder passwords with the actual test password used in fixtures."""
    applied = []
    for placeholder in PLACEHOLDER_PASSWORDS:
        # Handle double quotes
        if f'"{placeholder}"' in code:
            code = code.replace(f'"{placeholder}"', f'"{REAL_TEST_PASSWORD}"')
            applied.append(placeholder)
        # Handle single quotes
        if f"'{placeholder}'" in code:
            code = code.replace(f"'{placeholder}'", f"'{REAL_TEST_PASSWORD}'")
            if placeholder not in applied:
                applied.append(placeholder)
    if applied:
        return code, f"Replaced placeholder password(s): {', '.join(applied)} with test password"
    return code, ""


# Allowlist for CS7036: Parameter names that can receive safe defaults
MISSING_ARG_PARAM_ALLOWLIST = {"path", "file", "destination", "output"}


def parse_error_code(error: str) -> Optional[str]:
    """
    Extract error code from compiler error message.

    Args:
        error: Compiler error message

    Returns:
        Error code (e.g., "CS0103") or None
    """
    match = re.search(r'\b(CS\d+)\b', error)
    return match.group(1) if match else None


def parse_cs0103_error(error: str, using_directives: Dict[str, str] = None) -> Optional[str]:
    """
    Parse CS0103 error to extract undefined variable name.

    Error format: "The name 'outputPath' does not exist in the current context"

    Args:
        error: CS0103 error message
        using_directives: Optional family-specific using directives

    Returns:
        Variable name or None
    """
    # Use provided directives or fall back to base allowlist
    directives = using_directives if using_directives else USING_DIRECTIVE_ALLOWLIST

    match = re.search(r"The name '(\w+)' does not exist", error)
    if match:
        var_name = match.group(1)
        if var_name in UNDECLARED_VAR_ALLOWLIST:
            return var_name
        # Also check if this is actually a type name needing a using directive
        # (CS0103 fires instead of CS0246 when type is used as CompressionLevel.Optimal)
        if var_name in directives:
            return var_name
    return None


def parse_cs7036_error(error: str) -> Optional[str]:
    """
    Parse CS7036 error to extract missing parameter name.

    Error format: "There is no argument given that corresponds to the required parameter 'destinationFileName'"

    Args:
        error: CS7036 error message

    Returns:
        Parameter name or None
    """
    match = re.search(r"required parameter '(\w+)'", error)
    if match:
        param_name = match.group(1)
        # Check if parameter name contains any allowlisted keyword
        param_lower = param_name.lower()
        if any(keyword in param_lower for keyword in MISSING_ARG_PARAM_ALLOWLIST):
            return param_name
    return None


def parse_cs0246_error(error: str, using_directives: Dict[str, str] = None) -> Optional[str]:
    """
    Parse CS0246 error to extract missing type/namespace.

    Error format: "The type or namespace name 'Archive' could not be found"

    Args:
        error: CS0246 error message
        using_directives: Optional family-specific using directives

    Returns:
        Type/namespace name or None
    """
    # Use provided directives or fall back to base allowlist
    directives = using_directives if using_directives else USING_DIRECTIVE_ALLOWLIST

    match = re.search(r"The type or namespace name '(\w+)' could not be found", error)
    if match:
        type_name = match.group(1)
        if type_name in directives:
            return type_name
    return None


_SYSTEM_PREFERRED_TYPES = {
    "Path", "Directory", "File", "Console", "Environment", "Math",
    "Convert", "Encoding", "Stream", "Color", "Image", "Graphics",
    "Uri", "WebClient", "HttpClient", "Task", "Thread",
}


def parse_cs0104_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS0104 error to extract ambiguous type and preferred namespace.

    Error format: "'ParallelOptions' is an ambiguous reference between
    'Aspose.Zip.Saving.ParallelOptions' and 'System.Threading.Tasks.ParallelOptions'"

    For common BCL types (Path, Directory, File, etc.), prefers System namespace.
    For Aspose-specific types, prefers Aspose namespace.

    Returns:
        Tuple of (type_name, fully_qualified) or None
    """
    match = re.search(
        r"'(\w+)' is an ambiguous reference between '([\w.]+)' and '([\w.]+)'",
        error,
    )
    if match:
        type_name = match.group(1)
        ref1, ref2 = match.group(2), match.group(3)
        # For well-known System types, prefer the System namespace
        if type_name in _SYSTEM_PREFERRED_TYPES:
            if ref1.startswith("System."):
                return (type_name, ref1)
            elif ref2.startswith("System."):
                return (type_name, ref2)
        # Otherwise prefer the Aspose namespace
        if ref1.startswith("Aspose."):
            return (type_name, ref1)
        elif ref2.startswith("Aspose."):
            return (type_name, ref2)
    return None


def fix_cs0104_ambiguous_reference(code: str, type_name: str, fq_name: str) -> Tuple[str, str]:
    """
    Fix CS0104 by fully qualifying the ambiguous type with its Aspose namespace.

    Replaces patterns like 'new ParallelOptions' with 'new Aspose.Zip.Saving.ParallelOptions'.
    """
    patterns = [
        (rf'\bnew\s+{re.escape(type_name)}\b', f'new {fq_name}'),
        (rf'(?<![.\w]){re.escape(type_name)}(?=\s+\w)', fq_name),
    ]
    for pattern, replacement in patterns:
        new_code = re.sub(pattern, replacement, code)
        if new_code != code:
            return new_code, f"CS0104: Fully qualified ambiguous '{type_name}' as '{fq_name}'"
            code = new_code
    return code, ""


def parse_cs0234_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS0234 error: "The type or namespace name 'X' does not exist in the namespace 'Y'"

    Returns:
        Tuple of (type_name, wrong_namespace) or None
    """
    match = re.search(
        r"The type or namespace name '(\w+)' does not exist in the namespace '([\w.]+)'",
        error,
    )
    if match:
        return (match.group(1), match.group(2))
    return None


def fix_cs0234_namespace_missing(
    code: str, type_name: str, wrong_namespace: str, catalog=None
) -> Tuple[str, str]:
    """
    Fix CS0234: The type 'X' does not exist in namespace 'Y'.
    Strategy: Look up the correct namespace in the catalog, add/replace using directive.
    """
    if not catalog:
        return code, ""

    # Look up the correct namespace for the type in the catalog
    correct_ns = None
    if hasattr(catalog, "get_namespace_for_type"):
        correct_ns = catalog.get_namespace_for_type(type_name)
    elif isinstance(catalog, dict):
        # Catalog may be a dict with types section
        types = catalog.get("types", [])
        for t in types:
            if t.get("name") == type_name:
                correct_ns = t.get("namespace")
                break

    if not correct_ns or correct_ns == wrong_namespace:
        return code, ""

    correct_using = f"using {correct_ns};"
    wrong_using = f"using {wrong_namespace};"

    if correct_using in code:
        return code, ""  # Already has the correct using

    if wrong_using in code:
        # Replace the wrong using with the correct one
        fixed_code = code.replace(wrong_using, correct_using, 1)
        return fixed_code, f"CS0234: Replaced 'using {wrong_namespace}' with 'using {correct_ns}' for type '{type_name}'"
    else:
        # Add the correct using directive
        fixed_code, desc = fix_cs0246_missing_using(code, type_name, {type_name: correct_using})
        if desc:
            return fixed_code, f"CS0234: Added 'using {correct_ns}' for type '{type_name}' (was missing from '{wrong_namespace}')"
        return code, ""


def parse_cs1069_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS1069 error: "The type name 'X' could not be found in the namespace 'Y'"
    (type forwarding / assembly mismatch)

    Returns:
        Tuple of (type_name, current_namespace) or None
    """
    match = re.search(
        r"The type name '(\w+)' could not be found in the namespace '([\w.]+)'",
        error,
    )
    if match:
        return (match.group(1), match.group(2))
    return None


def fix_cs1069_type_forwarded(
    code: str, type_name: str, namespace: str, catalog=None
) -> Tuple[str, str]:
    """
    Fix CS1069: Type forwarded to another assembly.
    Strategy: Look up the correct namespace in the catalog, replace using directive.
    """
    if not catalog:
        return code, ""

    correct_ns = None
    if hasattr(catalog, "get_namespace_for_type"):
        correct_ns = catalog.get_namespace_for_type(type_name)
    elif isinstance(catalog, dict):
        types = catalog.get("types", [])
        for t in types:
            if t.get("name") == type_name:
                correct_ns = t.get("namespace")
                break

    if not correct_ns or correct_ns == namespace:
        return code, ""

    old_using = f"using {namespace};"
    new_using = f"using {correct_ns};"

    if new_using in code:
        return code, ""

    if old_using in code:
        fixed_code = code.replace(old_using, new_using, 1)
        return fixed_code, f"CS1069: Type '{type_name}' forwarded; replaced 'using {namespace}' with 'using {correct_ns}'"

    # Add the correct using if old one not found
    lines = code.split('\n')
    last_using = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('using ') and line.strip().endswith(';'):
            last_using = i
    if last_using >= 0:
        lines.insert(last_using + 1, new_using)
    else:
        lines.insert(0, new_using)
    fixed_code = '\n'.join(lines)
    return fixed_code, f"CS1069: Added 'using {correct_ns}' for forwarded type '{type_name}'"


def fix_cs1513_missing_brace(code: str) -> Tuple[str, str]:
    """
    Fix CS1513: Missing closing brace(s).
    Counts opening vs closing braces and appends missing ones.
    Conservative: only fixes if difference is 1-3 braces.
    """
    open_count = code.count('{')
    close_count = code.count('}')

    if open_count <= close_count:
        return code, ""

    missing = open_count - close_count

    if missing > 3:
        # Too many missing braces — likely a deeper structural issue
        return code, ""

    lines = code.rstrip().split('\n')
    for _ in range(missing):
        lines.append('}')

    fixed_code = '\n'.join(lines)
    return fixed_code, f"CS1513: Added {missing} missing closing brace(s)"


def fix_cs0246_missing_using(code: str, type_name: str, using_directives: Dict[str, str] = None) -> Tuple[str, str]:
    """
    Fix CS0246: Add missing using directive from allowlist.

    Args:
        code: Original code
        type_name: Missing type/namespace name
        using_directives: Optional family-specific using directives (merged with base allowlist)

    Returns:
        Tuple of (fixed_code, fix_description)
    """
    # Use provided directives or fall back to base allowlist
    directives = using_directives if using_directives else USING_DIRECTIVE_ALLOWLIST

    if type_name not in directives:
        return code, ""

    using_directive = directives[type_name]

    # Check if using directive already exists
    if using_directive in code:
        return code, ""

    # Find insertion point: after last using directive or at start
    lines = code.split('\n')
    last_using_idx = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('using ') and stripped.endswith(';'):
            last_using_idx = idx

    # Insert after last using directive
    if last_using_idx >= 0:
        lines.insert(last_using_idx + 1, using_directive)
    else:
        # No existing using directives, insert at top
        lines.insert(0, using_directive)

    fixed_code = '\n'.join(lines)
    fix_desc = f"CS0246: Added '{using_directive}' for type '{type_name}'"

    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_cs0103_undefined_name(code: str, var_name: str, using_directives: Dict[str, str] = None) -> Tuple[str, str]:
    """
    Fix CS0103: Insert variable definition with safe default,
    or add using directive if the name is actually a type.

    Args:
        code: Original code
        var_name: Undefined variable name
        using_directives: Optional family-specific using directives (merged with base allowlist)

    Returns:
        Tuple of (fixed_code, fix_description)
    """
    # Use provided directives or fall back to base allowlist
    directives = using_directives if using_directives else USING_DIRECTIVE_ALLOWLIST

    # If the "variable" is actually a type name, add a using directive instead
    if var_name in directives:
        return fix_cs0246_missing_using(code, var_name, using_directives)

    # Generate safe default based on variable name
    if var_name in ("dataDir", "baseDir", "sourceDir", "outputDir", "baseFolder",
                     "SourceDir", "OutputDir", "outputFolder", "output"):
        # Common Aspose gist boilerplate: path prefix variables for test files
        default_value = '""'
    else:
        default_value = 'Path.Combine(Path.GetTempPath(), "output")'
    definition = f'string {var_name} = {default_value};'

    # Find the first usage of the variable
    lines = code.split('\n')
    first_usage_idx = -1

    for idx, line in enumerate(lines):
        if re.search(rf'\b{var_name}\b', line):
            first_usage_idx = idx
            break

    if first_usage_idx < 0:
        # Variable not found in code, shouldn't happen but handle gracefully
        return code, ""

    # Find appropriate insertion point (start of same scope)
    # Simple heuristic: insert at the beginning of the method or block
    insertion_idx = first_usage_idx

    # Find the start of the containing method or block
    for idx in range(first_usage_idx - 1, -1, -1):
        line = lines[idx].strip()
        if line.endswith('{') or 'static void Main' in line or 'public static void' in line:
            insertion_idx = idx + 1
            break

    # Get the indentation of the first usage line
    if first_usage_idx < len(lines):
        indent_match = re.match(r'^(\s*)', lines[first_usage_idx])
        indent = indent_match.group(1) if indent_match else '        '
    else:
        indent = '        '

    # Insert the definition
    lines.insert(insertion_idx, f'{indent}{definition}')

    fixed_code = '\n'.join(lines)
    fix_desc = f"CS0103: Defined variable '{var_name}' with safe default"

    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_cs7036_missing_argument(code: str, param_name: str) -> Tuple[str, str]:
    """
    Fix CS7036: Supply safe default argument.

    Args:
        code: Original code
        param_name: Missing parameter name

    Returns:
        Tuple of (fixed_code, fix_description)
    """
    # Generate safe default argument
    default_arg = 'Path.Combine(Path.GetTempPath(), "output")'

    # Common method names that need path/file arguments
    priority_methods = [
        'ExtractToDirectory', 'Save', 'Extract', 'Create', 'Open',
        'SaveToFile', 'ExtractToFile', 'CreateDirectory', 'MoveTo',
        'CopyTo', 'WriteTo'
    ]

    # Find method call that's missing the argument
    lines = code.split('\n')
    fixed = False

    # First pass: look for priority methods
    for idx, line in enumerate(lines):
        # Skip method definitions
        if 'void Main' in line or 'static void' in line or 'public void' in line:
            continue

        # Skip lines that look like variable assignments with Path.GetTempPath()
        if '= Path.Combine(Path.GetTempPath()' in line:
            continue

        # Check for priority methods with empty parentheses
        for method_name in priority_methods:
            if f'{method_name}()' in line:
                new_line = line.replace(f'{method_name}()', f'{method_name}({default_arg})')
                lines[idx] = new_line
                fixed = True
                break

        if fixed:
            break

    # Second pass: look for trailing comma patterns
    if not fixed:
        for idx, line in enumerate(lines):
            if 'void Main' in line or 'static void' in line or 'public void' in line:
                continue

            if '= Path.Combine(Path.GetTempPath()' in line:
                continue

            # Pattern: method call with trailing comma (incomplete args)
            if re.search(r'\w+\s*\([^)]*,\s*\)', line):
                new_line = re.sub(r'(\w+\s*\([^)]*,)\s*\)', rf'\1 {default_arg})', line)
                lines[idx] = new_line
                fixed = True
                break

    # Third pass: any statement-level method call with empty parentheses
    if not fixed:
        for idx, line in enumerate(lines):
            if 'void Main' in line or 'static void' in line or 'public void' in line:
                continue

            if '= Path.Combine(Path.GetTempPath()' in line:
                continue

            # Skip constructor calls (lines with 'new')
            if 'new ' in line and '= ' in line:
                continue

            # Look for statement-level method calls
            if re.search(r'(\w+\.)?(\w+)\s*\(\s*\)\s*;', line):
                new_line = re.sub(r'(\w+)\s*\(\s*\)\s*;', rf'\1({default_arg});', line)
                lines[idx] = new_line
                fixed = True
                break

    if not fixed:
        # Fallback: couldn't find the specific location
        logger.warning(f"CS7036: Could not locate method call missing parameter '{param_name}'")
        return code, ""

    fixed_code = '\n'.join(lines)
    fix_desc = f"CS7036: Supplied default argument for parameter '{param_name}'"

    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_stream_disposal_pattern(code: str) -> Tuple[str, str]:
    """
    Fix stream disposal pattern: Remove premature using() disposal around streams
    that are consumed by archive operations.

    Handles three patterns:
    1. Block using: using (var ms = new MemoryStream()) { ... } archive.Save();
    2. Single-line using: using (var ms = new MemoryStream()) archive.CreateEntry(...);
    3. Declaration using: using var ms = new MemoryStream(); ... archive.Save();

    Transformation: Replace using with plain declaration, add explicit Dispose() after Save.

    Args:
        code: Original code

    Returns:
        Tuple of (fixed_code, fix_description)
    """
    stream_types = ['MemoryStream', 'FileStream']
    stream_pattern = '|'.join(stream_types)

    lines = code.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Pattern 1: Block using - using (var ms = new MemoryStream(...)) { ... }
        block_match = re.match(
            r'^(\s*)using\s*\(\s*var\s+(\w+)\s*=\s*new\s+(' + stream_pattern + r')\s*\(',
            line
        )
        if block_match:
            indent = block_match.group(1)
            stream_var = block_match.group(2)
            stream_type = block_match.group(3)

            using_start = i
            brace_count = 0
            using_end = -1
            found_create_entry = False

            for j in range(i, len(lines)):
                if '{' in lines[j]:
                    brace_count += lines[j].count('{')
                if '}' in lines[j]:
                    brace_count -= lines[j].count('}')
                    if brace_count == 0 and j > i:
                        using_end = j
                        break
                if stream_var in lines[j] and ('CreateEntry' in lines[j] or 'Extract' in lines[j]):
                    found_create_entry = True

            # Check for Save/Extract after the using block (search up to 25 lines)
            found_save_after = False
            save_line_idx = -1
            if using_end > 0 and found_create_entry:
                for j in range(using_end + 1, min(using_end + 25, len(lines))):
                    if 'Save(' in lines[j] or 'SaveAsync(' in lines[j] or 'Extract(' in lines[j]:
                        found_save_after = True
                        save_line_idx = j
                        break

            if using_end > 0 and found_create_entry and found_save_after:
                new_lines = []
                using_line = lines[using_start]
                using_line = re.sub(r'using\s*\(', '', using_line, count=1)
                using_line = re.sub(r'\)\s*\{?\s*$', ';', using_line)
                new_lines.append(using_line)

                for j in range(using_start + 1, using_end):
                    # Skip standalone opening brace line (part of using block structure)
                    if lines[j].strip() == '{':
                        continue
                    if lines[j].startswith(indent + '    '):
                        new_lines.append(indent + lines[j][len(indent) + 4:])
                    else:
                        new_lines.append(lines[j])

                result = []
                result.extend(lines[:using_start])
                result.extend(new_lines)
                result.extend(lines[using_end + 1:save_line_idx + 1])
                save_indent = re.match(r'^(\s*)', lines[save_line_idx]).group(1)
                result.append(f'{save_indent}{stream_var}.Dispose();')
                result.extend(lines[save_line_idx + 1:])

                fix_desc = f"STREAM_DISPOSAL: Moved {stream_type} disposal after archive.Save() to prevent ObjectDisposedException"
                logger.info(f"Applied fix: {fix_desc}")
                return '\n'.join(result), fix_desc

        # Pattern 2: Single-line using - using (var ms = new MemoryStream(...)) <statement>;
        # Use a simpler match to detect the pattern, then use paren counting for transformation
        single_match = re.match(
            r'^(\s*)using\s*\(\s*var\s+(\w+)\s*=\s*new\s+(' + stream_pattern + r')\s*\(',
            line
        )
        if single_match and '{' not in line:
            indent = single_match.group(1)
            stream_var = single_match.group(2)
            stream_type = single_match.group(3)

            # Next line should be the body statement (CreateEntry/Extract)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if stream_var in next_line and ('CreateEntry' in next_line or 'Extract' in next_line):
                    # Check for Save after the using statement (within 10 lines)
                    save_line_idx = -1
                    for j in range(i + 2, min(i + 12, len(lines))):
                        if 'Save(' in lines[j] or 'SaveAsync(' in lines[j] or 'Extract(' in lines[j]:
                            save_line_idx = j
                            break

                    if save_line_idx > 0:
                        # Transform: strip outer using(...) wrapper using paren counting
                        # Find the opening ( of using and the matching closing )
                        using_paren_start = line.index('(')
                        paren_depth = 0
                        using_paren_end = -1
                        for ci, ch in enumerate(line[using_paren_start:], using_paren_start):
                            if ch == '(':
                                paren_depth += 1
                            elif ch == ')':
                                paren_depth -= 1
                                if paren_depth == 0:
                                    using_paren_end = ci
                                    break
                        if using_paren_end > 0:
                            # Extract the declaration inside using(...)
                            inner = line[using_paren_start + 1:using_paren_end]
                            decl_line = indent + inner.strip() + ';'

                            result = []
                            result.extend(lines[:i])
                            result.append(decl_line)
                            result.extend(lines[i + 1:save_line_idx + 1])
                            save_indent = re.match(r'^(\s*)', lines[save_line_idx]).group(1)
                            result.append(f'{save_indent}{stream_var}.Dispose();')
                            result.extend(lines[save_line_idx + 1:])

                            fix_desc = f"STREAM_DISPOSAL: Moved {stream_type} disposal after archive.Save() to prevent ObjectDisposedException"
                            logger.info(f"Applied fix: {fix_desc}")
                            return '\n'.join(result), fix_desc

        # Pattern 3: C# 8 declaration using - using var ms = new MemoryStream(...);
        decl_match = re.match(
            r'^(\s*)using\s+var\s+(\w+)\s*=\s*new\s+(' + stream_pattern + r')\s*\(',
            line
        )
        if decl_match:
            indent = decl_match.group(1)
            stream_var = decl_match.group(2)
            stream_type = decl_match.group(3)

            # Check if stream is used in CreateEntry/Extract nearby
            found_create = False
            found_save = False
            save_line_idx = -1
            for j in range(i + 1, min(i + 15, len(lines))):
                if stream_var in lines[j] and ('CreateEntry' in lines[j] or 'Extract' in lines[j]):
                    found_create = True
                if 'Save(' in lines[j] or 'SaveAsync(' in lines[j]:
                    found_save = True
                    save_line_idx = j
                    break

            if found_create and found_save:
                # Replace "using var" with just "var" (remove early disposal)
                new_line = re.sub(r'^(\s*)using\s+var\b', r'\1var', line)
                result = []
                result.extend(lines[:i])
                result.append(new_line)
                result.extend(lines[i + 1:save_line_idx + 1])
                save_indent = re.match(r'^(\s*)', lines[save_line_idx]).group(1)
                result.append(f'{save_indent}{stream_var}.Dispose();')
                result.extend(lines[save_line_idx + 1:])

                fix_desc = f"STREAM_DISPOSAL: Removed early disposal of {stream_type}, added explicit Dispose() after Save()"
                logger.info(f"Applied fix: {fix_desc}")
                return '\n'.join(result), fix_desc

        i += 1

    return code, ""


# NOTE: ZIP-specific fix functions moved to semantic_microfixes_zip.py (TASK-2A)
# - fix_cs1503_rar_password_pattern -> fix_rar_archive_password
# - fix_cs1503_entries_string_index -> fix_entries_string_index
# - fix_placeholder_archive_paths -> fix_placeholder_archive_paths


def parse_cs0117_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS0117 error to extract type name and invalid member name.

    Error format: "'CompressionLevel' does not contain a definition for 'Normal'"

    Args:
        error: CS0117 error message

    Returns:
        Tuple of (type_name, member_name) or None
    """
    match = re.search(r"'(\w+)' does not contain a definition for '(\w+)'", error)
    if match:
        return (match.group(1), match.group(2))
    return None


def fix_cs0117_invalid_member(code: str, type_name: str, member_name: str, catalog=None) -> Optional[str]:
    """
    Fix CS0117 (invalid member) using catalog enum data + difflib fuzzy match.

    When a type does not contain a member (e.g. CompressionLevel.Normal),
    this function looks up valid enum members from the API catalog and
    finds the closest match using difflib.

    Args:
        code: Original code
        type_name: The type that doesn't contain the member (e.g. "CompressionLevel")
        member_name: The invalid member name (e.g. "Normal")
        catalog: Optional APICatalogService instance with enum data

    Returns:
        Fixed code string if a match was found, or None
    """
    if not catalog:
        return None
    members = catalog.get_enum_members(type_name)
    if not members:
        return None
    best_match = difflib.get_close_matches(member_name, members, n=1, cutoff=0.4)
    if best_match:
        old_ref = f"{type_name}.{member_name}"
        new_ref = f"{type_name}.{best_match[0]}"
        if old_ref in code:
            logger.info(f"CS0117: Fuzzy-matched '{old_ref}' -> '{new_ref}' (catalog enum lookup)")
            return code.replace(old_ref, new_ref)
    return None


def fix_cs1503_constructor_type(code: str, type_name: str, catalog=None) -> Optional[str]:
    """
    Fix CS1503 (wrong argument type) using catalog constructor data.

    When a constructor is called with the wrong argument type, this function
    looks up the catalog's constructor signatures for the type and tries to
    find one that takes an Options/Settings/LoadOptions parameter. If found,
    it suggests wrapping the argument in the appropriate Options object.

    Args:
        code: Original code
        type_name: The type whose constructor has a type mismatch
        catalog: Optional APICatalogService instance with constructor data

    Returns:
        Fixed code string if a suggestion was applied, or None
    """
    if not catalog:
        return None
    ctors = catalog.get_constructor_signatures(type_name)
    if not ctors:
        return None

    # Find constructor overloads that accept an Options/Settings/LoadOptions parameter
    options_ctor = None
    options_param_type = None
    for c in ctors:
        params_str = c.get("params", "")
        # params can be a string like "string? sourceFileName, ArchiveLoadOptions? options"
        # or a list of dicts — handle both formats
        if isinstance(params_str, str):
            # Parse comma-separated params from string
            for part in params_str.split(","):
                part = part.strip()
                # Check if param type contains Options/Settings/LoadOptions
                if any(kw in part for kw in ["Options", "Settings", "LoadOptions"]):
                    # Extract the type name (first token, removing nullable ?)
                    tokens = part.split()
                    if tokens:
                        options_param_type = tokens[0].rstrip("?")
                        options_ctor = c
                        break
        elif isinstance(params_str, list):
            for p in params_str:
                p_type = p.get("type", "")
                if any(kw in p_type for kw in ["Options", "Settings", "LoadOptions"]):
                    options_param_type = p_type.rstrip("?")
                    options_ctor = c
                    break
        if options_ctor:
            break

    if not options_ctor or not options_param_type:
        return None

    # Look for patterns like: new TypeName("arg1", "arg2")
    # where the second argument is a plain string that should be wrapped in Options
    # Common case: new RarArchive("file.rar", "password") ->
    #   new RarArchive("file.rar", new RarArchiveLoadOptions() { DecryptionPassword = "password" })
    pattern = rf'new\s+{re.escape(type_name)}\s*\(\s*("(?:[^"\\]|\\.)*")\s*,\s*("(?:[^"\\]|\\.)*")\s*\)'
    match = re.search(pattern, code)
    if match:
        first_arg = match.group(1)
        second_arg = match.group(2)

        # Determine the property name based on common patterns
        prop_name = "DecryptionPassword"  # Most common case for archive types
        if "Load" in options_param_type:
            prop_name = "DecryptionPassword"
        elif "Save" in options_param_type or "Saving" in options_param_type:
            prop_name = "Password"

        replacement = (
            f'new {type_name}({first_arg}, '
            f'new {options_param_type}() {{ {prop_name} = {second_arg} }})'
        )
        fixed_code = code[:match.start()] + replacement + code[match.end():]
        logger.info(
            f"CS1503: Replaced string arg with {options_param_type} in {type_name} constructor (catalog-driven)"
        )
        return fixed_code
    return None


def parse_cs1061_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS1061 error to extract type name and missing member name.

    Error format: "'Archive' does not contain a definition for 'SaveAsync'"
    Also matches: "'BaseGenerationParameters' does not contain a definition for 'ForeColor'"

    Returns:
        Tuple of (type_name, member_name) or None
    """
    match = re.search(r"'([\w.]+)' does not contain a definition for '(\w+)'", error)
    if match:
        return (match.group(1).split(".")[-1], match.group(2))
    return None


def fix_cs1061_member_not_found(code: str, type_name: str, member_name: str, catalog=None) -> Optional[str]:
    """
    Fix CS1061 (member not found) using catalog property+method data + difflib fuzzy match.

    Generic, catalog-driven: works for ANY family without hardcoded fix patterns.
    When a type does not contain a member (e.g. BaseGenerationParameters.ForeColor),
    this function looks up ALL known members (properties + methods) from the API catalog
    and finds the closest match using difflib.

    Args:
        code: Original code
        type_name: The type that doesn't contain the member
        member_name: The missing member name (e.g. "ForeColor")
        catalog: APICatalogService instance with property/method data

    Returns:
        Fixed code string if a match was found, or None
    """
    if not catalog:
        return None

    all_members = catalog.get_all_members(type_name)
    if not all_members:
        return None

    # Exact match means the member exists — CS1061 is about something else (skip)
    if member_name in all_members:
        return None

    best_match = difflib.get_close_matches(member_name, all_members, n=1, cutoff=0.4)
    if best_match:
        old_ref = f".{member_name}"
        new_ref = f".{best_match[0]}"
        if old_ref in code:
            logger.info(
                f"CS1061: Fuzzy-matched member '{type_name}.{member_name}' -> "
                f"'{type_name}.{best_match[0]}' (catalog property/method lookup)"
            )
            return code.replace(old_ref, new_ref)
    return None


def fix_cs0246_fuzzy_type(code: str, type_name: str, catalog=None) -> Optional[Tuple[str, str]]:
    """
    Fix CS0246 (type not found) by case-insensitive fuzzy matching against catalog types.

    When the exact type name isn't in the catalog (e.g. BarCodeGenerator with wrong casing),
    this function does case-insensitive lookup to find the correct name (BarcodeGenerator),
    replaces all occurrences in code, and adds the correct using directive.

    Args:
        code: Original code
        type_name: The missing type name from the CS0246 error
        catalog: APICatalogService instance

    Returns:
        Tuple of (fixed_code, fix_description) or None if no match
    """
    if not catalog:
        return None

    # Try case-insensitive match first
    correct_name = catalog.find_type_case_insensitive(type_name)
    if not correct_name or correct_name == type_name:
        # No case mismatch — try fuzzy match against all types
        all_types = catalog.get_all_types()
        matches = difflib.get_close_matches(type_name, all_types, n=1, cutoff=0.7)
        if matches:
            correct_name = matches[0]
        else:
            return None

    # Replace the wrong type name with the correct one in code
    fixed_code = re.sub(rf'\b{re.escape(type_name)}\b', correct_name, code)

    # Add using directive for the correct type
    using_directive = catalog.get_using_directive(correct_name)
    if using_directive and using_directive not in fixed_code:
        # Insert after last existing using statement
        lines = fixed_code.split('\n')
        last_using = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('using ') and line.strip().endswith(';'):
                last_using = i
        if last_using >= 0:
            lines.insert(last_using + 1, using_directive)
        else:
            lines.insert(0, using_directive)
        fixed_code = '\n'.join(lines)

    fix_desc = f"CS0246: Fuzzy-matched type '{type_name}' -> '{correct_name}' (catalog lookup)"
    logger.info(fix_desc)
    return (fixed_code, fix_desc)


def fix_namespace_redirect(code: str, type_name: str, catalog=None) -> Optional[Tuple[str, str]]:
    """
    Fix CS0246 by detecting namespace redirects (e.g. System.Drawing -> Aspose.Drawing).

    When code uses 'using System.Drawing;' but the type (e.g. Bitmap) actually lives in
    'Aspose.Drawing' per the catalog, replace the using directive. This is common when
    families wrap System.* namespaces with their own implementations.

    Args:
        code: Original code
        type_name: The missing type name
        catalog: APICatalogService instance

    Returns:
        Tuple of (fixed_code, fix_description) or None
    """
    if not catalog:
        return None

    # Check if the type exists in the catalog
    target_ns = catalog.get_namespace_for_type(type_name)
    if not target_ns:
        return None

    # Build a mapping of System.* -> Aspose.* namespace redirects from the catalog
    # If the type's namespace is something like "Aspose.Drawing", check if code has
    # a corresponding "System.Drawing" using directive
    if not target_ns.startswith("Aspose."):
        return None

    # Extract the suffix after "Aspose." (e.g. "Drawing" from "Aspose.Drawing")
    suffix = target_ns[len("Aspose."):]

    # Check for common system namespace prefixes that could be redirected
    system_ns_candidates = [
        f"System.{suffix}",
        f"System.{suffix}.Imaging",
    ]

    fixed_code = code
    redirected = []
    for sys_ns in system_ns_candidates:
        old_using = f"using {sys_ns};"
        if old_using in fixed_code:
            new_using = f"using {target_ns};"
            if target_ns == f"Aspose.{suffix}":
                # Direct redirect: System.Drawing -> Aspose.Drawing
                new_using = f"using {target_ns};"
            # Only redirect if new namespace isn't already imported
            if new_using not in fixed_code:
                fixed_code = fixed_code.replace(old_using, new_using)
                redirected.append(f"{sys_ns} -> {target_ns}")
            else:
                # Remove the duplicate system namespace
                fixed_code = fixed_code.replace(old_using + "\n", "")
                redirected.append(f"removed duplicate {sys_ns}")

    if not redirected:
        return None

    fix_desc = f"NS_REDIRECT: {'; '.join(redirected)} (catalog-driven)"
    logger.info(fix_desc)
    return (fixed_code, fix_desc)


def fix_cs1503_constructor_type_generic(code: str, error: str, catalog=None) -> Optional[Tuple[str, str]]:
    """
    Fix CS1503 (wrong argument type) using catalog constructor signatures.

    Generic version: when a constructor expects type Y but receives type X,
    and type Y has a constructor that accepts type X, wrap the argument:
        new Reader("path") -> new Reader(new Bitmap("path"))

    Also handles the reverse: if the catalog shows the correct overload takes
    a different parameter configuration.

    Args:
        code: Original code
        error: The full CS1503 error message
        catalog: APICatalogService instance

    Returns:
        Tuple of (fixed_code, fix_description) or None
    """
    if not catalog:
        return None

    # Parse: "cannot convert from 'string' to 'Bitmap'"
    convert_match = re.search(r"cannot convert from '([\w.]+)' to '([\w.]+)'", error)
    if not convert_match:
        return None

    from_type = convert_match.group(1).split(".")[-1]
    to_type = convert_match.group(2).split(".")[-1]

    # Check if the target type has a constructor that accepts the source type
    to_ctors = catalog.get_constructor_signatures(to_type)
    can_wrap = False
    for c in to_ctors:
        params_str = c.get("params", "")
        if isinstance(params_str, str) and from_type.lower() in params_str.lower():
            can_wrap = True
            break

    if not can_wrap:
        return None

    # Find all instances in code where a constructor has a raw from_type argument
    # that should be wrapped with new to_type(...)
    # Pattern: something(..."string_literal"...) where the arg should be wrapped
    # We look for: new SomeType("literal") where SomeType's ctor expects to_type not string

    # Try to find the enclosing constructor call and wrap the argument
    # Pattern: new EnclosingType("arg") -> new EnclosingType(new to_type("arg"))
    # We need to figure out which constructor call is failing
    enclosing_match = re.search(
        r"The best overloaded method match for '([\w.]+)\.([\w]+)\((.*?)\)'",
        error
    )
    if not enclosing_match:
        # Try alternate error format for constructor
        enclosing_match = re.search(r"'([\w.]+)\.(\w+)\(", error)

    # Generic approach: find string literal arguments that should be wrapped
    # Look for patterns: new Type("string_arg") where Type expects to_type
    # Replace "string_arg" with new to_type("string_arg")
    wrap_pattern = rf'(new\s+\w+\s*\(\s*)(\"[^\"]*\")(\s*[,\)])'
    matches = list(re.finditer(wrap_pattern, code))

    if not matches:
        return None

    fixed_code = code
    applied = False
    for m in reversed(matches):
        prefix = m.group(1)
        arg = m.group(2)
        suffix = m.group(3)

        # Only wrap if this looks like a from_type->to_type conversion
        new_arg = f"new {to_type}({arg})"
        replacement = f"{prefix}{new_arg}{suffix}"
        fixed_code = fixed_code[:m.start()] + replacement + fixed_code[m.end():]
        applied = True
        break  # Only fix the first match to be safe

    if not applied:
        return None

    # Ensure the to_type's namespace is imported
    using_dir = catalog.get_using_directive(to_type)
    if using_dir and using_dir not in fixed_code:
        lines = fixed_code.split('\n')
        last_using = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('using ') and line.strip().endswith(';'):
                last_using = i
        if last_using >= 0:
            lines.insert(last_using + 1, using_dir)
        else:
            lines.insert(0, using_dir)
        fixed_code = '\n'.join(lines)

    fix_desc = f"CS1503: Wrapped {from_type} arg with new {to_type}(...) (catalog constructor match)"
    logger.info(fix_desc)
    return (fixed_code, fix_desc)


def fix_placeholder_directory_paths(code: str) -> Tuple[str, str]:
    """
    Fix placeholder directory paths that don't exist at runtime.

    Blog examples use placeholder folder names like:
    - "zip_folder" -> "." (current directory with test data)
    - "folder" -> "."
    - "YourFolderPath" -> "."
    - "AnimationImages" -> "."
    - "sourceDir" -> "."
    - "inputFolder" -> "."

    These are used in Directory.GetFiles() or similar calls expecting
    a directory of files to compress.
    """
    placeholder_dirs = [
        "zip_folder", "folder", "YourFolderPath", "AnimationImages",
        "sourceDir", "inputFolder", "sourceFolder", "inputDirectory",
        "folderPath", "directoryPath", "sourcePath"
    ]

    applied = []
    fixed_code = code

    for placeholder in placeholder_dirs:
        # Match: "placeholder" in context that looks like a directory path
        # Pattern 1: Directory.GetFiles("placeholder", ...)
        pattern1 = rf'(Directory\.(GetFiles|GetDirectories|EnumerateFiles|Exists)\s*\(\s*)"{placeholder}"'
        if re.search(pattern1, fixed_code):
            fixed_code = re.sub(pattern1, rf'\1"."', fixed_code)
            applied.append(placeholder)
            continue

        # Pattern 2: new DirectoryInfo("placeholder")
        pattern2 = rf'new\s+DirectoryInfo\s*\(\s*"{placeholder}"\s*\)'
        if re.search(pattern2, fixed_code):
            fixed_code = re.sub(pattern2, 'new DirectoryInfo(".")', fixed_code)
            applied.append(placeholder)
            continue

        # Pattern 3: Path.Combine("placeholder", ...)
        pattern3 = rf'Path\.Combine\s*\(\s*"{placeholder}"'
        if re.search(pattern3, fixed_code):
            fixed_code = re.sub(pattern3, 'Path.Combine("."', fixed_code)
            applied.append(placeholder)
            continue

        # Pattern 4: CreateEntries("placeholder") - Aspose archive method
        pattern4 = rf'(\.CreateEntries\s*\(\s*)"{placeholder}"'
        if re.search(pattern4, fixed_code):
            fixed_code = re.sub(pattern4, rf'\1"."', fixed_code)
            applied.append(placeholder)
            continue

        # Pattern 5: standalone string assignment
        pattern5 = rf'=\s*"{placeholder}"\s*;'
        if re.search(pattern5, fixed_code):
            fixed_code = re.sub(pattern5, '= ".";', fixed_code)
            applied.append(placeholder)

    if not applied:
        return code, ""

    fix_desc = f"RUNTIME: Replaced placeholder directories with '.': {', '.join(set(applied))}"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_extract_output_directory(code: str) -> Tuple[str, str]:
    """
    Fix runtime DirectoryNotFoundException for Extract calls targeting subdirectories.

    Injects Directory.CreateDirectory before Extract("subdir/file") calls
    to ensure the output directory exists at runtime.
    """
    # Match: .Extract("path/with/subdir/file.ext")
    pattern = r'([ \t]*)(\w+)\.Extract\s*\(\s*"([^"]*[/\\][^"]+)"\s*\)'
    matches = list(re.finditer(pattern, code))
    if not matches:
        return code, ""

    lines = code.split('\n')
    insertions = []  # (line_idx, indent, dir_path)

    for match in matches:
        # Find which line this match is on
        pos = match.start()
        line_num = code[:pos].count('\n')
        indent = match.group(1)
        extract_path = match.group(3)
        # Get directory portion of the path
        dir_part = extract_path.rsplit('/', 1)[0] if '/' in extract_path else extract_path.rsplit('\\', 1)[0]
        if dir_part and dir_part != extract_path:
            insertions.append((line_num, indent, dir_part))

    if not insertions:
        return code, ""

    # Insert Directory.CreateDirectory calls (in reverse to preserve line numbers)
    for line_num, indent, dir_part in reversed(insertions):
        create_line = f'{indent}Directory.CreateDirectory(@"{dir_part}");'
        lines.insert(line_num, create_line)

    fixed_code = '\n'.join(lines)

    # Ensure using System.IO is present
    if 'using System.IO;' not in fixed_code:
        using_lines = [i for i, line in enumerate(fixed_code.split('\n')) if line.strip().startswith('using ') and line.strip().endswith(';')]
        if using_lines:
            flines = fixed_code.split('\n')
            flines.insert(using_lines[-1] + 1, 'using System.IO;')
            fixed_code = '\n'.join(flines)

    fix_desc = f"RUNTIME: Injected Directory.CreateDirectory for {len(insertions)} Extract output path(s)"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_plugins_to_lowcode(code: str) -> Tuple[str, str]:
    """
    Fix deprecated Aspose.*.Plugins namespace → Aspose.*.LowCode.

    Starting in 2025, Aspose products renamed the Plugins namespace to LowCode:
    - Aspose.Pdf.Plugins → Aspose.Pdf.LowCode
    - Aspose.Words.Plugins → Aspose.Words.LowCode
    - Aspose.Cells.Plugins → Aspose.Cells.LowCode
    etc.

    Blog/doc examples may still reference the old Plugins namespace.
    """
    if '.Plugins' not in code:
        return code, ""

    # Replace Aspose.*.Plugins with Aspose.*.LowCode
    fixed = re.sub(
        r'\bAspose\.(\w+)\.Plugins\b',
        r'Aspose.\1.LowCode',
        code,
    )
    if fixed != code:
        return fixed, "Renamed deprecated Aspose.*.Plugins to Aspose.*.LowCode"
    return code, ""


def fix_cs1061_save_async(code: str) -> Tuple[str, str]:
    """
    Fix CS1061: Archive does not contain a definition for 'SaveAsync'.

    Aspose.Zip Archive has Save() but NOT SaveAsync(). Blog examples
    (especially ASP.NET snippets) incorrectly use SaveAsync.

    Transforms:
        await archive.SaveAsync(stream);
    Into:
        archive.Save(stream);

    Also handles: await archive.SaveAsync(...) in any context.
    """
    if 'SaveAsync' not in code:
        return code, ""

    # Replace await <var>.SaveAsync( with <var>.Save(
    fixed_code = re.sub(
        r'\bawait\s+(\w+)\.SaveAsync\s*\(',
        r'\1.Save(',
        code
    )
    # Also handle SaveAsync without await (rare but possible)
    if fixed_code == code:
        fixed_code = re.sub(
            r'\.SaveAsync\s*\(',
            '.Save(',
            code
        )

    if fixed_code == code:
        return code, ""

    fix_desc = "CS1061: Replaced SaveAsync with Save (Aspose.Zip Archive has no SaveAsync method)"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_cs0246_password_protection(code: str) -> Tuple[str, str]:
    """
    Fix CS0246: 'PasswordProtection' type does not exist in Aspose.Zip.

    Blog examples incorrectly use a non-existent PasswordProtection class.
    The correct API is ArchiveLoadOptions with DecryptionPassword property.

    Transforms:
        new Archive(stream, new PasswordProtection("pw"))
    Into:
        new Archive(stream, new ArchiveLoadOptions() { DecryptionPassword = "pw" })
    """
    pattern = r'new\s+PasswordProtection\s*\(\s*("(?:[^"\\]|\\.)*")\s*\)'
    match = re.search(pattern, code)
    if not match:
        return code, ""

    password_arg = match.group(1)
    replacement = f'new ArchiveLoadOptions() {{ DecryptionPassword = {password_arg} }}'
    fixed_code = code[:match.start()] + replacement + code[match.end():]

    # Ensure using Aspose.Zip is present (for ArchiveLoadOptions)
    if 'using Aspose.Zip;' not in fixed_code:
        lines = fixed_code.split('\n')
        using_lines = [i for i, line in enumerate(lines) if line.strip().startswith('using ') and line.strip().endswith(';')]
        if using_lines:
            lines.insert(using_lines[-1] + 1, 'using Aspose.Zip;')
        else:
            lines.insert(0, 'using Aspose.Zip;')
        fixed_code = '\n'.join(lines)

    fix_desc = "CS0246: Replaced PasswordProtection with ArchiveLoadOptions (PasswordProtection doesn't exist in Aspose.Zip)"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_archive_password_as_path(code: str) -> Tuple[str, str]:
    """
    Fix Archive("password") where password is mistakenly passed as file path.

    Blog examples sometimes show:
        new Archive("your_password")  or  new Aspose.Zip.Archive("p@s$")
    where the constructor expects a FILE PATH, not a password.

    Correct API:
        new Archive("sample.zip", new ArchiveLoadOptions() { DecryptionPassword = "p@s$" })

    Detection: new Archive(str) where str matches a known placeholder password
    or the real test password.
    """
    all_passwords = PLACEHOLDER_PASSWORDS + [REAL_TEST_PASSWORD]

    for pw in all_passwords:
        # Match: new Archive("password") or new Aspose.Zip.Archive("password")
        pattern = rf'new\s+(?:Aspose\.Zip\.)?Archive\s*\(\s*"{re.escape(pw)}"\s*\)'
        match = re.search(pattern, code)
        if match:
            replacement = f'new Archive("sample.zip", new ArchiveLoadOptions() {{ DecryptionPassword = "{REAL_TEST_PASSWORD}" }})'
            fixed_code = code[:match.start()] + replacement + code[match.end():]

            # Ensure using Aspose.Zip is present
            if 'using Aspose.Zip;' not in fixed_code and 'using Aspose.Zip;' not in fixed_code:
                lines = fixed_code.split('\n')
                using_lines = [i for i, line in enumerate(lines)
                               if line.strip().startswith('using ') and line.strip().endswith(';')]
                if using_lines:
                    lines.insert(using_lines[-1] + 1, 'using Aspose.Zip;')
                else:
                    lines.insert(0, 'using Aspose.Zip;')
                fixed_code = '\n'.join(lines)

            fix_desc = f"RUNTIME: Replaced Archive(\"{pw}\") — password passed as file path, rewrote to Archive(\"sample.zip\", ArchiveLoadOptions)"
            logger.info(f"Applied fix: {fix_desc}")
            return fixed_code, fix_desc

    return code, ""


def fix_partial_snippet_undefined_vars(code: str) -> Tuple[str, str]:
    """
    Inject missing variable declarations for partial code snippets.

    Blog examples sometimes show only the inner body of a loop or method,
    referencing variables like 'rarArchive', 'entry', 'file' that are
    defined in the surrounding (but not shown) context.

    This fix detects undefined archive-related variables and injects
    the minimum declarations needed to make the snippet compilable.
    """
    applied = []
    fixed_code = code
    lines = code.strip().split('\n')
    meaningful = [l.strip() for l in lines if l.strip() and not l.strip().startswith('//')]

    # Skip if code already has enough context (class, Main, etc.)
    if any('class ' in l for l in meaningful) or any('static void Main' in l for l in meaningful):
        return code, ""

    # Pattern 1: 'rarArchive' referenced but not declared
    if re.search(r'\brarArchive\b', code) and not re.search(r'\bvar\s+rarArchive\b|\bRarArchive\s+rarArchive\b', code):
        injection = 'using var rarArchive = new RarArchive("archive.rar");\n'
        fixed_code = injection + fixed_code
        applied.append('rarArchive')

    # Pattern 2: 'entry' referenced but not declared (in context of archive iteration)
    if (re.search(r'\bentry\.Open\b|\bentry\.Name\b|\bentry\.Extract\b', fixed_code)
            and not re.search(r'\bvar\s+entry\b|\bforeach\s*\(.*\bentry\b', fixed_code)):
        # This is a loop body — need archive + loop context
        if 'rarArchive' not in fixed_code:
            pre = 'using var archive = new RarArchive("archive.rar");\nforeach (var entry in archive.Entries) {\n'
        else:
            pre = 'foreach (var entry in rarArchive.Entries) {\n'
        fixed_code = pre + fixed_code + '\n}'
        applied.append('entry (loop context)')

    # Pattern 3: 'file' used as stream but not declared (file.Write pattern)
    if (re.search(r'\bfile\.Write\b', fixed_code)
            and not re.search(r'\bvar\s+file\b|\bFileStream\s+file\b|\bStream\s+file\b', fixed_code)):
        injection = 'using var file = File.Create(entry.Name);\n'
        # Insert before the first line that uses 'file'
        flines = fixed_code.split('\n')
        for i, line in enumerate(flines):
            if 'file.Write' in line or 'file.' in line:
                indent = len(line) - len(line.lstrip())
                flines.insert(i, ' ' * indent + injection.rstrip())
                break
        fixed_code = '\n'.join(flines)
        applied.append('file (FileStream)')

    if not applied:
        return code, ""

    fix_desc = f"PARTIAL_SNIPPET: Injected missing variable declarations: {', '.join(applied)}"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_aspnet_minimal_boilerplate(code: str) -> Tuple[str, str]:
    """
    Fix ASP.NET minimal API snippets missing builder/app boilerplate.

    Blog examples show ASP.NET patterns like app.MapGet() without the
    necessary WebApplication builder setup. Inject the boilerplate.

    Transforms:
        app.MapGet("/endpoint", async (HttpContext ctx) => { ... });
    Into:
        var builder = WebApplication.CreateBuilder();
        var app = builder.Build();
        app.MapGet("/endpoint", async (HttpContext ctx) => { ... });
        app.Run();
    """
    # Only apply if code uses app. patterns without defining app
    has_app_ref = bool(re.search(r'\bapp\.(MapGet|MapPost|MapPut|MapDelete|Map|Use|Run)\b', code))
    has_builder = 'WebApplication.CreateBuilder' in code or 'WebApplicationBuilder' in code
    has_app_def = 'var app' in code or 'var app' in code

    if not has_app_ref or has_builder or has_app_def:
        return code, ""

    boilerplate = "var builder = WebApplication.CreateBuilder();\nvar app = builder.Build();\n\n"
    suffix = ""
    if 'app.Run()' not in code and 'app.Run(' not in code:
        suffix = "\n\napp.Run();"

    fixed_code = boilerplate + code + suffix
    fix_desc = "ASPNET: Injected WebApplication builder boilerplate for partial ASP.NET minimal API snippet"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_aspnet_run_blocking(code: str) -> Tuple[str, str]:
    """
    Replace blocking app.Run() with non-blocking validation for ASP.NET examples.

    ASP.NET minimal API's app.Run() starts a web server that blocks forever,
    causing runtime timeout. Replace with a quick start/stop that validates
    the configuration without blocking.

    Transforms:
        app.Run();
    Into:
        await app.StartAsync();
        await app.StopAsync();
        Console.WriteLine("ASP.NET app validated.");
    """
    is_aspnet = bool(re.search(
        r'\b(WebApplication|app\.MapGet|app\.MapPost|app\.MapPut|app\.MapDelete)\b', code
    ))
    if not is_aspnet:
        return code, ""

    replaced = False

    # Replace await app.RunAsync(); or await app.RunAsync(token);
    new_code = re.sub(
        r'await\s+app\.RunAsync\s*\([^)]*\)\s*;',
        'await app.StartAsync();\nawait app.StopAsync();\nConsole.WriteLine("ASP.NET app validated.");',
        code
    )
    if new_code != code:
        replaced = True
        code = new_code

    # Replace app.Run(); or app.Run(url);
    new_code = re.sub(
        r'(?<!await\s)app\.Run\s*\([^)]*\)\s*;',
        'await app.StartAsync();\nawait app.StopAsync();\nConsole.WriteLine("ASP.NET app validated.");',
        code
    )
    if new_code != code:
        replaced = True
        code = new_code

    if not replaced:
        return code, ""

    # Ensure top-level async: if code has Main method, make sure it's async
    # For top-level statements, add await keyword support
    fix_desc = "ASPNET: Replaced blocking app.Run() with non-blocking StartAsync/StopAsync for validation"
    logger.info(f"Applied fix: {fix_desc}")
    return code, fix_desc


# NOTE: ZIP-specific archive iteration fix moved to semantic_microfixes_zip.py (TASK-2A)
# - fix_archive_iteration_try_catch


def fix_file_exists_on_extract(code: str) -> Tuple[str, str]:
    """
    Fix runtime IOException: Cannot create file because it already exists.

    When ExtractToDirectory extracts to a folder that already contains files
    (e.g., placeholder.txt from test data setup), extraction fails.

    Injects cleanup code before ExtractToDirectory calls:
        if (Directory.Exists("output_folder")) Directory.Delete("output_folder", true);
        Directory.CreateDirectory("output_folder");
    """
    # Match: .ExtractToDirectory("path")
    pattern = r'([ \t]*)(\w+)\.ExtractToDirectory\s*\(\s*("(?:[^"\\]|\\.)*")\s*\)'
    matches = list(re.finditer(pattern, code))
    if not matches:
        return code, ""

    lines = code.split('\n')
    insertions = []  # (line_idx, indent, dir_path)

    for match in matches:
        pos = match.start()
        line_num = code[:pos].count('\n')
        indent = match.group(1)
        dir_path = match.group(3)  # includes quotes

        # Don't add cleanup for "." (current directory)
        if dir_path.strip('"') == '.':
            continue

        insertions.append((line_num, indent, dir_path))

    if not insertions:
        return code, ""

    # Insert cleanup calls (in reverse to preserve line numbers)
    for line_num, indent, dir_path in reversed(insertions):
        cleanup = (
            f'{indent}if (Directory.Exists({dir_path})) Directory.Delete({dir_path}, true);\n'
            f'{indent}Directory.CreateDirectory({dir_path});'
        )
        lines.insert(line_num, cleanup)

    fixed_code = '\n'.join(lines)

    # Ensure using System.IO is present
    if 'using System.IO;' not in fixed_code:
        flines = fixed_code.split('\n')
        using_lines = [i for i, line in enumerate(flines) if line.strip().startswith('using ') and line.strip().endswith(';')]
        if using_lines:
            flines.insert(using_lines[-1] + 1, 'using System.IO;')
        else:
            flines.insert(0, 'using System.IO;')
        fixed_code = '\n'.join(flines)

    fix_desc = f"RUNTIME: Injected directory cleanup before ExtractToDirectory to prevent file collision"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


# NOTE: ZIP-specific CompressionLevel fix functions moved to semantic_microfixes_zip.py (TASK-2A)
# - fix_compression_level_invalid_values
# - fix_deflate_compression_settings_constructor
# - fix_compression_level_parameter


def proactive_add_using_directives(code: str, namespace_map: Dict[str, str]) -> Tuple[str, List[str]]:
    """
    Proactively add missing using directives based on detected API usage in code.

    This function scans the code for Aspose API class references and adds the necessary
    using directives BEFORE compilation, preventing CS0246 errors from occurring.

    Args:
        code: Original code to analyze
        namespace_map: Dictionary mapping API class names to their namespaces
                      (e.g., {"SevenZipArchive": "Aspose.Zip.SevenZip"})

    Returns:
        Tuple of (modified_code, list_of_fix_descriptions)

    Example:
        >>> namespace_map = {"SevenZipArchive": "Aspose.Zip.SevenZip"}
        >>> code = "class Program { void Main() { var a = new SevenZipArchive(); } }"
        >>> fixed_code, fixes = proactive_add_using_directives(code, namespace_map)
        >>> "using Aspose.Zip.SevenZip;" in fixed_code
        True
    """
    if not namespace_map:
        # No catalog available, can't add using directives proactively
        return code, []

    # Detect API usage in code
    detected_apis = []
    for api_class in namespace_map.keys():
        # Look for patterns indicating API usage:
        # - new ApiClass(...) - instantiation
        # - ApiClass. - static member access
        # - ApiClass< - generic type usage
        # - <ApiClass> - generic type parameter
        # - (ApiClass param) - parameter declaration
        patterns = [
            rf'\bnew\s+{re.escape(api_class)}\b',
            rf'\b{re.escape(api_class)}\.',
            rf'\b{re.escape(api_class)}<',
            rf'<{re.escape(api_class)}>',
            rf'\({re.escape(api_class)}\s+\w+\)',
        ]
        if any(re.search(pattern, code) for pattern in patterns):
            detected_apis.append(api_class)

    if not detected_apis:
        # No APIs detected, no using directives needed
        return code, []

    # Extract existing using directives from code
    existing_usings = set()
    using_pattern = r'using\s+([\w\.]+)\s*;'
    for match in re.finditer(using_pattern, code):
        existing_usings.add(match.group(1))

    # Find missing using directives
    needed_usings = set()
    for api in detected_apis:
        namespace = namespace_map.get(api)
        if namespace and namespace not in existing_usings:
            needed_usings.add(namespace)

    if not needed_usings:
        # All necessary using directives already present
        return code, []

    # Add missing using directives
    # Find insertion point: after last existing using directive, or at top
    lines = code.split('\n')
    last_using_idx = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('using ') and stripped.endswith(';'):
            last_using_idx = idx

    # Insert new using directives (sorted for consistency)
    sorted_usings = sorted(needed_usings)
    if last_using_idx >= 0:
        # Insert after last existing using directive
        for using_ns in reversed(sorted_usings):
            lines.insert(last_using_idx + 1, f'using {using_ns};')
    else:
        # No existing using directives, insert at top
        for using_ns in reversed(sorted_usings):
            lines.insert(0, f'using {using_ns};')

    fixed_code = '\n'.join(lines)

    # Create fix descriptions
    fixes = [f"PROACTIVE: Added using directive '{ns}' for detected API usage" for ns in sorted_usings]

    logger.info(f"Proactively added {len(sorted_usings)} using directive(s): {', '.join(sorted_usings)}")
    return fixed_code, fixes


def fix_data_dir_patterns(code: str, replacements: Dict[str, str]) -> Tuple[str, str]:
    """Apply configurable data-dir pattern replacements for CS file examples.

    Replaces family-specific data directory resolution patterns (e.g.
    RunExamples.GetDataDir_*(), MyDir, ArtifactsDir) with workspace-relative paths.

    Args:
        code: C# source code
        replacements: Dict of {regex_pattern: replacement_string}

    Returns:
        (modified_code, description_of_changes)
    """
    changes = []
    for pattern, replacement in replacements.items():
        # If replacement already has quotes, use as-is; otherwise add quotes
        if replacement.startswith('"') or replacement.startswith('@"'):
            repl = replacement
        else:
            repl = f'"{replacement}"'
        new_code, count = re.subn(pattern, repl, code)
        if count > 0:
            changes.append(f"{count}x {pattern}")
            code = new_code
    desc = f"Data dir fix: {'; '.join(changes)}" if changes else ""
    return code, desc


def fix_example_namespace_collision(code: str, package_namespace: str = "") -> Tuple[str, str]:
    """Strip example namespaces that collide with the NuGet package namespace.

    Removes namespace wrappers like:
      namespace Aspose.Pdf.Examples.CSharp.AsposePDF.Text { ... }
      namespace DocsExamples.Programming_with_Documents { ... }

    This prevents CS0234/CS0246 errors caused by the example namespace
    partially matching the NuGet package namespace.

    Args:
        code: C# source code
        package_namespace: NuGet package root namespace (e.g. "Aspose.Pdf")

    Returns:
        (modified_code, description_of_changes)
    """
    # Match namespace declarations that look like example namespaces
    ns_pattern = re.compile(
        r'^(\s*)namespace\s+([\w.]+)\s*\{',
        re.MULTILINE
    )
    match = ns_pattern.search(code)
    if not match:
        return code, ""

    ns_name = match.group(2)

    # Only strip if it looks like an example namespace (contains "Examples", "Docs", etc.)
    # or if it starts with the package namespace and has extra segments
    is_example_ns = any(kw in ns_name for kw in ['Examples', 'DocsExamples', 'ApiExamples', 'Samples'])
    is_collision = package_namespace and ns_name.startswith(package_namespace) and ns_name != package_namespace

    if not (is_example_ns or is_collision):
        return code, ""

    # Find the matching closing brace by counting braces from the namespace opening
    ns_start = match.start()
    brace_start = match.end() - 1  # Position of the opening {
    depth = 1
    pos = brace_start + 1
    while pos < len(code) and depth > 0:
        if code[pos] == '{':
            depth += 1
        elif code[pos] == '}':
            depth -= 1
        pos += 1

    if depth != 0:
        return code, ""

    ns_end = pos  # Position after the closing }

    # Extract the inner content (between { and })
    inner = code[brace_start + 1:ns_end - 1]

    # Dedent the inner content by the namespace indentation
    indent = match.group(1)
    if indent:
        lines = inner.split('\n')
        dedented = []
        for line in lines:
            if line.startswith(indent + '    '):
                dedented.append(line[len(indent) + 4:])
            elif line.startswith(indent):
                dedented.append(line[len(indent):])
            elif line.strip() == '':
                dedented.append('')
            else:
                dedented.append(line)
        inner = '\n'.join(dedented)

    # Reconstruct: code before namespace + inner content + code after namespace
    result = code[:ns_start] + inner.strip() + '\n' + code[ns_end:].lstrip()

    return result.strip(), f"Stripped example namespace '{ns_name}'"


# ---------------------------------------------------------------------------
# HEAL-37: Proactive catalog-driven error-inference functions
# These scan code BEFORE compilation and validate against the API catalog
# to catch errors that would otherwise require a compile-fail-fix cycle.
# ---------------------------------------------------------------------------


def proactive_validate_enum_members(code: str, catalog) -> Tuple[str, List[str]]:
    """
    Proactively validate enum member references against the API catalog.

    Scans code for EnumType.MemberName patterns and fuzzy-fixes invalid members
    BEFORE compilation, eliminating CS0117 errors proactively.
    """
    if not catalog or not hasattr(catalog, 'get_all_enums'):
        return code, []

    all_enums = catalog.get_all_enums()
    if not all_enums:
        return code, []

    fixes = []
    fixed_code = code

    for enum_name, valid_members in all_enums.items():
        if not valid_members:
            continue
        pattern = rf'\b{re.escape(enum_name)}\.(\w+)\b'
        for match in re.finditer(pattern, fixed_code):
            member_name = match.group(1)
            if member_name in valid_members:
                continue
            best = difflib.get_close_matches(member_name, valid_members, n=1, cutoff=0.4)
            if best:
                old_ref = f"{enum_name}.{member_name}"
                new_ref = f"{enum_name}.{best[0]}"
                fixed_code = fixed_code.replace(old_ref, new_ref)
                fixes.append(
                    f"PROACTIVE_ENUM: Fixed '{old_ref}' -> '{new_ref}' (catalog enum validation)"
                )
                logger.info(f"PROACTIVE_ENUM: {old_ref} -> {new_ref}")

    return fixed_code, fixes


def proactive_validate_constructors(code: str, catalog) -> Tuple[str, List[str]]:
    """
    Proactively validate constructor calls against catalog signatures.

    Scans for new TypeName(args) patterns and checks if the arguments match
    known overloads. Wraps string args in Options objects where needed.
    Catches CS1503 proactively.
    """
    if not catalog or not hasattr(catalog, 'get_constructor_signatures'):
        return code, []

    fixes = []
    fixed_code = code

    # Find all constructor calls: new TypeName(...)
    ctor_pattern = r'new\s+(\w+)\s*\('
    seen_types = set()
    for match in re.finditer(ctor_pattern, fixed_code):
        type_name = match.group(1)
        if type_name in seen_types:
            continue
        seen_types.add(type_name)

        ctors = catalog.get_constructor_signatures(type_name)
        if not ctors:
            continue

        result = fix_cs1503_constructor_type(fixed_code, type_name, catalog=catalog)
        if result is not None and result != fixed_code:
            fixed_code = result
            fixes.append(
                f"PROACTIVE_CTOR: Wrapped constructor arg for '{type_name}' "
                f"with Options type (catalog constructor validation)"
            )
            logger.info(f"PROACTIVE_CTOR: Wrapped arg for {type_name}")

    return fixed_code, fixes


def proactive_normalize_type_casing(code: str, catalog) -> Tuple[str, List[str]]:
    """
    Proactively fix type name casing against the API catalog.

    Scans for type references and does case-insensitive matching to fix
    casing errors (e.g. BarCodeGenerator -> BarcodeGenerator) BEFORE
    compilation, eliminating CS0246 errors proactively.
    """
    if not catalog or not hasattr(catalog, 'find_type_case_insensitive'):
        return code, []

    fixes = []
    fixed_code = code

    # Find candidate type names: PascalCase identifiers after 'new', '.', or standalone
    type_pattern = r'(?:new\s+)([A-Z]\w{2,})\b'
    seen = set()

    for match in re.finditer(type_pattern, fixed_code):
        type_name = match.group(1)
        if type_name in seen:
            continue
        seen.add(type_name)

        # Skip if already valid in catalog
        if catalog.validate_symbol(type_name):
            continue

        # Try case-insensitive match
        correct_name = catalog.find_type_case_insensitive(type_name)
        if correct_name and correct_name != type_name:
            fixed_code = re.sub(rf'\b{re.escape(type_name)}\b', correct_name, fixed_code)

            # Add using directive for the correct type if missing
            using_dir = catalog.get_using_directive(correct_name)
            if using_dir and using_dir not in fixed_code:
                lines = fixed_code.split('\n')
                last_using = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('using ') and line.strip().endswith(';'):
                        last_using = i
                if last_using >= 0:
                    lines.insert(last_using + 1, using_dir)
                else:
                    lines.insert(0, using_dir)
                fixed_code = '\n'.join(lines)

            fixes.append(
                f"PROACTIVE_CASING: Fixed type casing '{type_name}' -> '{correct_name}'"
            )
            logger.info(f"PROACTIVE_CASING: {type_name} -> {correct_name}")

    return fixed_code, fixes


def apply_semantic_microfixes(
    code: str,
    errors: List[str],
    family: str = None,
    registry: 'FamilyServiceRegistry' = None,
    catalog: 'APICatalogService' = None
) -> Tuple[str, List[str]]:
    """
    Apply diagnostic-driven semantic micro-fixes (family-aware).

    Fixes are applied in order:
    0. STREAM_DISPOSAL: Fix premature stream disposal (always applied)
    1. Family-specific proactive fixes (if family specified)
    2. Generic proactive fixes (passwords, directories, ASP.NET, etc.)
    3. Error-driven fixes (CS1513, CS0104, CS0246, CS0234, CS1069, CS0103, CS7036, CS0117, CS1503)

    When a catalog (APICatalogService) is provided, CS0117 and CS1503 errors
    can be fixed dynamically using enum member data and constructor signatures
    from the API catalog. Existing hardcoded fixes remain as fallback.

    Args:
        code: Original code
        errors: Compilation errors
        family: Product family identifier (e.g., 'zip', 'words') - optional for backwards compat
        registry: FamilyServiceRegistry instance for family-aware using directives - optional
        catalog: APICatalogService instance for dynamic enum/constructor fixes - optional

    Returns:
        Tuple of (fixed_code, applied_fixes)
    """
    fixed_code = code
    applied_fixes = []

    # Get family-specific using directives from registry (if available)
    using_directives = None
    if family and registry:
        try:
            catalog_directives = registry.get_using_directives(family)
            # Merge with base allowlist (catalog takes precedence over base)
            using_directives = {**USING_DIRECTIVE_ALLOWLIST, **catalog_directives}
            logger.info(
                f"Loaded {len(catalog_directives)} catalog using directives for family '{family}' "
                f"(merged with {len(USING_DIRECTIVE_ALLOWLIST)} base directives, "
                f"total: {len(using_directives)} unique types)"
            )
        except Exception as e:
            logger.warning(f"Failed to load using directives for family '{family}': {e}")
            using_directives = USING_DIRECTIVE_ALLOWLIST
    else:
        # Fallback to base allowlist if no family/registry provided
        using_directives = USING_DIRECTIVE_ALLOWLIST
        if family:
            logger.debug(f"No registry provided for family '{family}', using base allowlist only ({len(using_directives)} types)")

    # 0. Fix stream disposal patterns (proactive, always run - generic)
    fixed_code, fix_desc = fix_stream_disposal_pattern(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 1. Apply family-specific proactive fixes (LEGACY — generic catalog-driven fixers
    # in steps 6-8 below now handle most of these cases autonomously. Per-family files
    # are kept as fallback for truly unique patterns that can't be derived from catalog.)
    if family == 'zip':
        try:
            from .semantic_microfixes_zip import ZIP_SPECIFIC_FIXES
            for fix_fn in ZIP_SPECIFIC_FIXES:
                fixed_code, fix_desc = fix_fn(fixed_code)
                if fix_desc:
                    applied_fixes.append(fix_desc)
                    logger.debug(f"[LEGACY] Per-family fix applied: {fix_desc} (consider catalog-driven alternative)")
        except ImportError as e:
            logger.warning(f"Failed to import ZIP-specific fixes: {e}")
    elif family == 'words':
        try:
            from .semantic_microfixes_words import WORDS_SPECIFIC_FIXES
            for fix_fn in WORDS_SPECIFIC_FIXES:
                fixed_code, fix_desc = fix_fn(fixed_code)
                if fix_desc:
                    applied_fixes.append(fix_desc)
                    logger.debug(f"[LEGACY] Per-family fix applied: {fix_desc} (consider catalog-driven alternative)")
        except ImportError as e:
            logger.warning(f"Failed to import Words-specific fixes: {e}")

    # 2. Generic proactive fixes (apply to all families)

    # 2a. Fix Extract output directory (ensure directories exist before Extract)
    fixed_code, fix_desc = fix_extract_output_directory(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2b. Fix placeholder directory paths (zip_folder, folder, etc.)
    fixed_code, fix_desc = fix_placeholder_directory_paths(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2c. Fix CS1061: SaveAsync -> Save (Aspose.Zip has no SaveAsync)
    fixed_code, fix_desc = fix_cs1061_save_async(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2c2. Fix deprecated Plugins → LowCode namespace (Aspose 2025+ rename)
    fixed_code, fix_desc = fix_plugins_to_lowcode(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2d. Fix ASP.NET minimal API boilerplate (inject builder/app)
    fixed_code, fix_desc = fix_aspnet_minimal_boilerplate(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2e. Fix ASP.NET blocking app.Run() -> non-blocking StartAsync/StopAsync
    fixed_code, fix_desc = fix_aspnet_run_blocking(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2f. Fix CS0246: PasswordProtection -> ArchiveLoadOptions
    fixed_code, fix_desc = fix_cs0246_password_protection(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2g. Fix placeholder passwords proactively (before runtime)
    fixed_code, fix_desc = fix_placeholder_passwords(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2h-pre. Fix Archive("password") wrong constructor: password passed as file path
    fixed_code, fix_desc = fix_archive_password_as_path(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2h-pre2. Inject missing variable declarations for partial snippets
    fixed_code, fix_desc = fix_partial_snippet_undefined_vars(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2h. Fix file-exists collision on ExtractToDirectory
    fixed_code, fix_desc = fix_file_exists_on_extract(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    # 2i. Proactive catalog-driven validation (HEAL-37)
    # Scans code for patterns and validates against the API catalog WITHOUT
    # needing compiler errors. Each catches a category of errors proactively.
    if catalog:
        fixed_code, enum_fixes = proactive_validate_enum_members(fixed_code, catalog)
        applied_fixes.extend(enum_fixes)

        fixed_code, ctor_fixes = proactive_validate_constructors(fixed_code, catalog)
        applied_fixes.extend(ctor_fixes)

        fixed_code, casing_fixes = proactive_normalize_type_casing(fixed_code, catalog)
        applied_fixes.extend(casing_fixes)

    if not errors:
        return fixed_code, applied_fixes

    # 3. Error-driven fixes (use family-aware using directives)

    # Parse all errors and categorize by type
    cs0246_types = []
    cs0246_raw_types = []  # type names extracted from raw error (before allowlist filter)
    cs0103_vars = []
    cs7036_params = []
    cs0104_refs = []  # (type_name, fully_qualified_name)
    cs0117_members = []  # (type_name, member_name)
    cs1061_members = []  # (type_name, member_name) — new: generic member-not-found
    cs1503_types = []  # type_name (from error context)
    cs1503_raw_errors = []  # raw error strings for generic constructor fix
    cs0234_types = []  # (type_name, wrong_namespace) — namespace redirect
    cs1069_types = []  # (type_name, current_namespace) — type forwarding
    cs1513_detected = False  # missing closing brace

    for error in errors:
        error_code = parse_error_code(error)

        if error_code == "CS0246":
            type_name = parse_cs0246_error(error, using_directives)
            if type_name and type_name not in cs0246_types:
                cs0246_types.append(type_name)
            # Also capture the raw type name (before allowlist filter) for fuzzy matching
            raw_match = re.search(r"The type or namespace name '(\w+)' could not be found", error)
            if raw_match:
                raw_name = raw_match.group(1)
                if raw_name not in cs0246_raw_types:
                    cs0246_raw_types.append(raw_name)

        elif error_code == "CS0103":
            var_name = parse_cs0103_error(error, using_directives)
            if var_name and var_name not in cs0103_vars:
                cs0103_vars.append(var_name)

        elif error_code == "CS7036":
            param_name = parse_cs7036_error(error)
            if param_name and param_name not in cs7036_params:
                cs7036_params.append(param_name)

        elif error_code == "CS0104":
            parsed = parse_cs0104_error(error)
            if parsed and parsed not in cs0104_refs:
                cs0104_refs.append(parsed)

        elif error_code == "CS0117":
            parsed = parse_cs0117_error(error)
            if parsed and parsed not in cs0117_members:
                cs0117_members.append(parsed)

        elif error_code == "CS1061":
            parsed = parse_cs1061_error(error)
            if parsed and parsed not in cs1061_members:
                cs1061_members.append(parsed)

        elif error_code == "CS1503":
            # Extract type name from CS1503 error for catalog-driven constructor fix
            # Error format: "Argument N: cannot convert from 'X' to 'Y'"
            type_match = re.search(r"cannot convert from '(\w+)' to '([\w.]+)'", error)
            if type_match:
                target_type = type_match.group(2).split(".")[-1]  # Get simple name
                if target_type not in cs1503_types:
                    cs1503_types.append(target_type)
                cs1503_raw_errors.append(error)

        elif error_code == "CS0234":
            parsed = parse_cs0234_error(error)
            if parsed and parsed not in cs0234_types:
                cs0234_types.append(parsed)

        elif error_code == "CS1069":
            parsed = parse_cs1069_error(error)
            if parsed and parsed not in cs1069_types:
                cs1069_types.append(parsed)

        elif error_code == "CS1513":
            cs1513_detected = True

    # Apply structural fix first (CS1513), then namespace fixes, then others
    # 0a. Fix CS1513: Missing closing braces (structural — must come first)
    if cs1513_detected:
        fixed_code, fix_desc = fix_cs1513_missing_brace(fixed_code)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # Apply fixes in order: CS0104 -> CS0246 -> CS0234 -> CS1069 -> CS0103 -> CS7036

    # 0. Fix CS0104: Ambiguous References (fully qualify with Aspose namespace)
    for type_name, fq_name in cs0104_refs:
        fixed_code, fix_desc = fix_cs0104_ambiguous_reference(fixed_code, type_name, fq_name)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 1. Fix CS0246: Missing Using Directives
    for type_name in cs0246_types:
        fixed_code, fix_desc = fix_cs0246_missing_using(fixed_code, type_name, using_directives)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 1b. Fix CS0234: Namespace Redirect (type not in namespace)
    for type_name, wrong_ns in cs0234_types:
        fixed_code, fix_desc = fix_cs0234_namespace_missing(fixed_code, type_name, wrong_ns, catalog=catalog)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 1c. Fix CS1069: Type Forwarded to Different Assembly
    for type_name, ns in cs1069_types:
        fixed_code, fix_desc = fix_cs1069_type_forwarded(fixed_code, type_name, ns, catalog=catalog)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 2. Fix CS0103: Undefined Variables
    for var_name in cs0103_vars:
        fixed_code, fix_desc = fix_cs0103_undefined_name(fixed_code, var_name, using_directives)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 3. Fix CS7036: Missing Arguments
    for param_name in cs7036_params:
        fixed_code, fix_desc = fix_cs7036_missing_argument(fixed_code, param_name)
        if fix_desc:
            applied_fixes.append(fix_desc)

    # 4. Fix CS0117: Invalid Member (catalog-driven enum fuzzy match)
    for type_name, member_name in cs0117_members:
        result = fix_cs0117_invalid_member(fixed_code, type_name, member_name, catalog=catalog)
        if result is not None:
            fixed_code = result
            applied_fixes.append(
                f"CS0117: Replaced '{type_name}.{member_name}' with catalog-matched valid member"
            )
        else:
            logger.debug(
                f"CS0117: No catalog match for '{type_name}.{member_name}' "
                f"(catalog {'available' if catalog else 'not available'})"
            )

    # 5. Fix CS1503: Wrong Argument Type (catalog-driven constructor suggestion)
    for target_type in cs1503_types:
        result = fix_cs1503_constructor_type(fixed_code, target_type, catalog=catalog)
        if result is not None:
            fixed_code = result
            applied_fixes.append(
                f"CS1503: Applied catalog-driven constructor fix for '{target_type}'"
            )
        else:
            logger.debug(
                f"CS1503: No catalog constructor fix for '{target_type}' "
                f"(catalog {'available' if catalog else 'not available'})"
            )

    # 6. Fix CS1061: Member Not Found (catalog-driven property/method fuzzy match)
    for type_name, member_name in cs1061_members:
        result = fix_cs1061_member_not_found(fixed_code, type_name, member_name, catalog=catalog)
        if result is not None:
            fixed_code = result
            applied_fixes.append(
                f"CS1061: Fuzzy-matched '{type_name}.{member_name}' to catalog member"
            )
        else:
            logger.debug(
                f"CS1061: No catalog match for '{type_name}.{member_name}' "
                f"(catalog {'available' if catalog else 'not available'})"
            )

    # 7. Fix CS0246: Fuzzy Type Matching + Namespace Redirect (catalog-driven)
    # Only for types that weren't handled by the standard CS0246 using-directive fix
    already_fixed_types = set(cs0246_types)
    for raw_type in cs0246_raw_types:
        if raw_type in already_fixed_types:
            continue  # Already fixed by standard CS0246 handler

        # 7a. Try namespace redirect first (System.Drawing -> Aspose.Drawing)
        result = fix_namespace_redirect(fixed_code, raw_type, catalog=catalog)
        if result is not None:
            fixed_code, fix_desc = result
            applied_fixes.append(fix_desc)
            continue

        # 7b. Try fuzzy type matching (BarCodeGenerator -> BarcodeGenerator)
        result = fix_cs0246_fuzzy_type(fixed_code, raw_type, catalog=catalog)
        if result is not None:
            fixed_code, fix_desc = result
            applied_fixes.append(fix_desc)
        else:
            logger.debug(
                f"CS0246: No fuzzy type match for '{raw_type}' "
                f"(catalog {'available' if catalog else 'not available'})"
            )

    # 8. Fix CS1503: Generic Constructor Type Wrapping (catalog-driven)
    # Only for errors not handled by the specialized CS1503 handler above
    for raw_error in cs1503_raw_errors:
        result = fix_cs1503_constructor_type_generic(fixed_code, raw_error, catalog=catalog)
        if result is not None:
            fixed_code, fix_desc = result
            applied_fixes.append(fix_desc)

    logger.info(f"Applied {len(applied_fixes)} semantic micro-fixes")
    return fixed_code, applied_fixes


# ============================================================================
# UNIT TESTS
# ============================================================================

def test_parse_error_code():
    """Test error code extraction."""
    assert parse_error_code("error CS0103: The name 'x' does not exist") == "CS0103"
    assert parse_error_code("error CS7036: Missing argument") == "CS7036"
    assert parse_error_code("error CS0246: Type not found") == "CS0246"
    assert parse_error_code("Some other error") is None
    print("[PASS] test_parse_error_code")


def test_parse_cs0103_error():
    """Test CS0103 error parsing."""
    # Valid cases (in allowlist)
    assert parse_cs0103_error("The name 'outputPath' does not exist in the current context") == "outputPath"
    assert parse_cs0103_error("The name 'destinationPath' does not exist") == "destinationPath"
    assert parse_cs0103_error("The name 'archivePath' does not exist") == "archivePath"
    assert parse_cs0103_error("The name 'filePath' does not exist") == "filePath"

    # Invalid cases (not in allowlist)
    assert parse_cs0103_error("The name 'randomVar' does not exist") is None
    assert parse_cs0103_error("The name 'someOtherVar' does not exist") is None

    print("[PASS] test_parse_cs0103_error")


def test_parse_cs7036_error():
    """Test CS7036 error parsing."""
    # Valid cases (contains allowlisted keywords)
    assert parse_cs7036_error("required parameter 'destinationFileName'") == "destinationFileName"
    assert parse_cs7036_error("required parameter 'outputPath'") == "outputPath"
    assert parse_cs7036_error("required parameter 'filePath'") == "filePath"
    assert parse_cs7036_error("required parameter 'destinationDir'") == "destinationDir"

    # Invalid cases (no allowlisted keywords)
    assert parse_cs7036_error("required parameter 'count'") is None
    assert parse_cs7036_error("required parameter 'index'") is None

    print("[PASS] test_parse_cs7036_error")


def test_parse_cs0246_error():
    """Test CS0246 error parsing."""
    # Valid cases (in allowlist)
    assert parse_cs0246_error("The type or namespace name 'Archive' could not be found") == "Archive"
    assert parse_cs0246_error("The type or namespace name 'SevenZipArchive' could not be found") == "SevenZipArchive"
    assert parse_cs0246_error("The type or namespace name 'RarArchive' could not be found") == "RarArchive"

    # Invalid cases (not in allowlist)
    assert parse_cs0246_error("The type or namespace name 'UnknownType' could not be found") is None

    print("[PASS] test_parse_cs0246_error")


def test_fix_cs0246_missing_using():
    """Test CS0246 fix: adding using directives."""
    # Test adding to existing using directives
    code = """using System;
using System.IO;

class Program {
    static void Main() {
        Archive archive = new Archive();
    }
}"""

    fixed, desc = fix_cs0246_missing_using(code, "Archive")
    assert "using Aspose.Zip;" in fixed
    assert desc == "CS0246: Added 'using Aspose.Zip;' for type 'Archive'"
    assert fixed.count("using Aspose.Zip;") == 1

    # Test adding when no using directives exist
    code_no_usings = """class Program {
    static void Main() {
        Archive archive = new Archive();
    }
}"""

    fixed, desc = fix_cs0246_missing_using(code_no_usings, "Archive")
    assert "using Aspose.Zip;" in fixed
    assert fixed.startswith("using Aspose.Zip;")

    # Test when using directive already exists
    code_exists = """using System;
using Aspose.Zip;

class Program {}"""

    fixed, desc = fix_cs0246_missing_using(code_exists, "Archive")
    assert fixed == code_exists
    assert desc == ""

    print("[PASS] test_fix_cs0246_missing_using")


def test_fix_cs0103_undefined_name():
    """Test CS0103 fix: defining undefined variables."""
    code = """using System;
using System.IO;

class Program {
    static void Main() {
        File.Copy("source.txt", outputPath);
    }
}"""

    fixed, desc = fix_cs0103_undefined_name(code, "outputPath")
    assert 'string outputPath = Path.Combine(Path.GetTempPath(), "output");' in fixed
    assert desc == "CS0103: Defined variable 'outputPath' with safe default"

    # Verify the definition is inserted before usage
    lines = fixed.split('\n')
    def_idx = None
    usage_idx = None

    for idx, line in enumerate(lines):
        if 'string outputPath' in line:
            def_idx = idx
        if 'File.Copy' in line and 'outputPath' in line:
            usage_idx = idx

    assert def_idx is not None
    assert usage_idx is not None
    assert def_idx < usage_idx

    print("[PASS] test_fix_cs0103_undefined_name")


def test_fix_cs7036_missing_argument():
    """Test CS7036 fix: supplying missing arguments."""
    # Test: empty parentheses
    code = """using System;

class Program {
    static void Main() {
        archive.ExtractToDirectory();
    }
}"""

    fixed, desc = fix_cs7036_missing_argument(code, "destinationFileName")
    assert 'ExtractToDirectory(Path.Combine(Path.GetTempPath(), "output"))' in fixed
    assert desc == "CS7036: Supplied default argument for parameter 'destinationFileName'"

    # Test: trailing comma
    code_trailing = """using System;

class Program {
    static void Main() {
        archive.Save("input.zip", );
    }
}"""

    fixed, desc = fix_cs7036_missing_argument(code_trailing, "destinationPath")
    assert 'archive.Save("input.zip", Path.Combine(Path.GetTempPath(), "output"))' in fixed

    print("[PASS] test_fix_cs7036_missing_argument")


def test_apply_semantic_microfixes_integration():
    """Test complete integration of all fixes."""
    code = """using System;

class Program {
    static void Main() {
        Archive archive = new Archive();
        archive.ExtractToDirectory();
        File.Copy("source.txt", outputPath);
    }
}"""

    errors = [
        "error CS0246: The type or namespace name 'Archive' could not be found",
        "error CS0103: The name 'outputPath' does not exist in the current context",
        "error CS7036: There is no argument given that corresponds to the required parameter 'destinationFileName'",
    ]

    fixed, applied = apply_semantic_microfixes(code, errors)

    # Verify all fixes were applied
    assert len(applied) == 3
    assert "using Aspose.Zip;" in fixed
    assert 'string outputPath' in fixed
    assert 'ExtractToDirectory(Path.Combine' in fixed

    # Verify fix order
    assert "CS0246" in applied[0]
    assert "CS0103" in applied[1]
    assert "CS7036" in applied[2]

    print("[PASS] test_apply_semantic_microfixes_integration")


def test_apply_semantic_microfixes_empty():
    """Test with no errors."""
    code = "class Program {}"
    fixed, applied = apply_semantic_microfixes(code, [])
    assert fixed == code
    assert applied == []
    print("[PASS] test_apply_semantic_microfixes_empty")


def test_apply_semantic_microfixes_no_applicable_fixes():
    """Test with errors that don't match allowlists."""
    code = "class Program {}"
    errors = [
        "error CS0103: The name 'unknownVar' does not exist",
        "error CS0246: The type or namespace name 'UnknownType' could not be found",
    ]

    fixed, applied = apply_semantic_microfixes(code, errors)
    assert fixed == code
    assert applied == []
    print("[PASS] test_apply_semantic_microfixes_no_applicable_fixes")


def test_fix_stream_disposal_pattern():
    """Test stream disposal pattern fix."""
    code = """using System;
using System.IO;
using Aspose.Zip;

class Program {
    static void Main() {
        using (var archive = new Archive()) {
            using (var ms = new MemoryStream()) {
                archive.CreateEntry("file.txt", ms);
            }
            archive.Save("output.zip");
        }
    }
}"""

    fixed, desc = fix_stream_disposal_pattern(code)

    # Verify fix was applied
    assert desc != ""
    assert "STREAM_DISPOSAL" in desc
    assert "using (var ms = new MemoryStream())" not in fixed
    assert "var ms = new MemoryStream();" in fixed
    assert "ms.Dispose();" in fixed

    # Verify Dispose is after Save
    lines = fixed.split('\n')
    save_idx = -1
    dispose_idx = -1
    for i, line in enumerate(lines):
        if 'Save(' in line:
            save_idx = i
        if 'ms.Dispose()' in line:
            dispose_idx = i

    assert save_idx > 0, "Save call not found"
    assert dispose_idx > 0, "Dispose call not found"
    assert dispose_idx > save_idx, "Dispose should be after Save"

    print("[PASS] test_fix_stream_disposal_pattern")


def test_fix_stream_disposal_pattern_filestream():
    """Test stream disposal pattern with FileStream."""
    code = """using System;
using System.IO;
using Aspose.Zip;

class Program {
    static void Main() {
        var archive = new Archive();
        using (var fs = new FileStream("input.txt", FileMode.Open)) {
            archive.CreateEntry("file.txt", fs);
        }
        archive.Save("output.zip");
    }
}"""

    fixed, desc = fix_stream_disposal_pattern(code)

    # Verify fix was applied
    assert desc != ""
    assert "STREAM_DISPOSAL" in desc
    assert "using (var fs = new FileStream" not in fixed
    assert "var fs = new FileStream" in fixed
    assert "fs.Dispose();" in fixed

    print("[PASS] test_fix_stream_disposal_pattern_filestream")


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("Running Semantic Micro-Fixes Unit Tests")
    print("="*60 + "\n")

    test_parse_error_code()
    test_parse_cs0103_error()
    test_parse_cs7036_error()
    test_parse_cs0246_error()
    test_fix_cs0246_missing_using()
    test_fix_cs0103_undefined_name()
    test_fix_cs7036_missing_argument()
    test_fix_stream_disposal_pattern()
    test_fix_stream_disposal_pattern_filestream()
    test_apply_semantic_microfixes_integration()
    test_apply_semantic_microfixes_empty()
    test_apply_semantic_microfixes_no_applicable_fixes()

    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60 + "\n")


def example_usage():
    """Demonstrate usage of semantic micro-fixes."""
    print("\n" + "="*60)
    print("Example Usage: Semantic Micro-Fixes")
    print("="*60 + "\n")

    code = """using System;

class Program {
    static void Main() {
        Archive archive = new Archive("sample.zip");
        archive.ExtractToDirectory();
        Console.WriteLine("Extracted to: " + outputPath);
    }
}"""

    errors = [
        "error CS0246: The type or namespace name 'Archive' could not be found",
        "error CS0103: The name 'outputPath' does not exist in the current context",
        "error CS7036: There is no argument given that corresponds to the required parameter 'destinationPath'",
    ]

    print("ORIGINAL CODE:")
    print(code)
    print("\nCOMPILER ERRORS:")
    for error in errors:
        print(f"  - {error}")

    fixed_code, applied_fixes = apply_semantic_microfixes(code, errors)

    print("\nAPPLIED FIXES:")
    for fix in applied_fixes:
        print(f"  - {fix}")

    print("\nFIXED CODE:")
    print(fixed_code)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "example":
        example_usage()
    else:
        run_all_tests()
