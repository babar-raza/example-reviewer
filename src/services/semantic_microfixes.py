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
UNDECLARED_VAR_ALLOWLIST = {"outputPath", "destinationPath", "archivePath", "filePath", "dataDir"}


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


def parse_cs0104_error(error: str) -> Optional[Tuple[str, str]]:
    """
    Parse CS0104 error to extract ambiguous type and preferred Aspose namespace.

    Error format: "'ParallelOptions' is an ambiguous reference between
    'Aspose.Zip.Saving.ParallelOptions' and 'System.Threading.Tasks.ParallelOptions'"

    Returns:
        Tuple of (type_name, aspose_fully_qualified) or None
    """
    match = re.search(
        r"'(\w+)' is an ambiguous reference between '([\w.]+)' and '([\w.]+)'",
        error,
    )
    if match:
        type_name = match.group(1)
        ref1, ref2 = match.group(2), match.group(3)
        # Prefer the Aspose namespace
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
    if var_name == "dataDir":
        # Common Aspose gist boilerplate: dataDir is a path prefix for test files
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


def apply_semantic_microfixes(
    code: str,
    errors: List[str],
    family: str = None,
    registry: 'FamilyServiceRegistry' = None
) -> Tuple[str, List[str]]:
    """
    Apply diagnostic-driven semantic micro-fixes (family-aware).

    Fixes are applied in order:
    0. STREAM_DISPOSAL: Fix premature stream disposal (always applied)
    1. Family-specific proactive fixes (if family specified)
    2. Generic proactive fixes (passwords, directories, ASP.NET, etc.)
    3. Error-driven fixes (CS0246, CS0103, CS7036, CS0104)

    Args:
        code: Original code
        errors: Compilation errors
        family: Product family identifier (e.g., 'zip', 'words') - optional for backwards compat
        registry: FamilyServiceRegistry instance for family-aware using directives - optional

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

    # 1. Apply family-specific proactive fixes
    if family == 'zip':
        try:
            from .semantic_microfixes_zip import ZIP_SPECIFIC_FIXES
            for fix_fn in ZIP_SPECIFIC_FIXES:
                fixed_code, fix_desc = fix_fn(fixed_code)
                if fix_desc:
                    applied_fixes.append(fix_desc)
        except ImportError as e:
            logger.warning(f"Failed to import ZIP-specific fixes: {e}")
    elif family == 'words':
        try:
            from .semantic_microfixes_words import WORDS_SPECIFIC_FIXES
            for fix_fn in WORDS_SPECIFIC_FIXES:
                fixed_code, fix_desc = fix_fn(fixed_code)
                if fix_desc:
                    applied_fixes.append(fix_desc)
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

    # 2h. Fix file-exists collision on ExtractToDirectory
    fixed_code, fix_desc = fix_file_exists_on_extract(fixed_code)
    if fix_desc:
        applied_fixes.append(fix_desc)

    if not errors:
        return fixed_code, applied_fixes

    # 3. Error-driven fixes (use family-aware using directives)

    # Parse all errors and categorize by type
    cs0246_types = []
    cs0103_vars = []
    cs7036_params = []
    cs0104_refs = []  # (type_name, fully_qualified_name)

    for error in errors:
        error_code = parse_error_code(error)

        if error_code == "CS0246":
            type_name = parse_cs0246_error(error, using_directives)
            if type_name and type_name not in cs0246_types:
                cs0246_types.append(type_name)

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

    # Apply fixes in order: CS0104 -> CS0246 -> CS0103 -> CS7036

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
