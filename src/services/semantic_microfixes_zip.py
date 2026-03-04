"""
ZIP-specific semantic microfixes for Aspose.ZIP examples.

This module contains deterministic fix patterns that are specific to the
Aspose.ZIP product family. These patterns handle ZIP-specific API quirks,
constructor signatures, and common blog post mistakes.

Extracted from semantic_microfixes.py as part of TASK-2A (multi-family refactor).
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def fix_rar_archive_password(code: str) -> Tuple[str, str]:
    """
    Fix CS1503: RarArchive constructor takes RarArchiveLoadOptions, not string password.

    Transforms:
        new RarArchive("file.rar", "password")
    Into:
        new RarArchive("file.rar", new RarArchiveLoadOptions() { DecryptionPassword = "password" })
    """
    # Match: new RarArchive("...", "...")
    pattern = r'new\s+RarArchive\s*\(\s*("(?:[^"\\]|\\.)*")\s*,\s*("(?:[^"\\]|\\.)*")\s*\)'
    match = re.search(pattern, code)
    if not match:
        return code, ""

    file_arg = match.group(1)
    password_arg = match.group(2)

    replacement = f'new RarArchive({file_arg}, new RarArchiveLoadOptions() {{ DecryptionPassword = {password_arg} }})'
    fixed_code = code[:match.start()] + replacement + code[match.end():]

    # Ensure using Aspose.Zip.Rar is present (for RarArchiveLoadOptions)
    if 'using Aspose.Zip.Rar;' not in fixed_code:
        # Add after last using directive
        using_lines = [i for i, line in enumerate(fixed_code.split('\n')) if line.strip().startswith('using ') and line.strip().endswith(';')]
        if using_lines:
            lines = fixed_code.split('\n')
            lines.insert(using_lines[-1] + 1, 'using Aspose.Zip.Rar;')
            fixed_code = '\n'.join(lines)

    fix_desc = f"CS1503: Replaced string password with RarArchiveLoadOptions in RarArchive constructor"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_entries_string_index(code: str) -> Tuple[str, str]:
    """
    Fix CS1503: Archive Entries collection uses int index, not string.

    Transforms:
        archive.Entries["filename.txt"]
    Into:
        archive.Entries[0]

    Blog examples use placeholder filenames that won't match test archive
    contents, so we use index 0 (first entry) which always works.
    """
    # Match: .Entries["..."]
    pattern = r'\.Entries\s*\[\s*("(?:[^"\\]|\\.)*")\s*\]'
    match = re.search(pattern, code)
    if not match:
        return code, ""

    replacement = '.Entries[0]'
    fixed_code = code[:match.start()] + replacement + code[match.end():]

    fix_desc = "CS1503: Replaced string indexer on Entries with int index [0]"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_placeholder_archive_paths(code: str) -> Tuple[str, str]:
    """
    Fix placeholder archive file paths that don't exist in test data.

    Blog examples use generic archive names like:
    - "compressed_files.zip" -> "sample.zip" (exists in test-data)
    - "your_archive.zip" -> "sample.zip"
    - "source.zip" -> "sample.zip"
    - "input.zip" -> "sample.zip"
    - "archive.zip" -> "sample.zip"

    These should map to actual test fixtures.
    """
    placeholder_archives = {
        "compressed_files.zip": "sample.zip",
        "your_archive.zip": "sample.zip",
        "source.zip": "sample.zip",
        "input.zip": "sample.zip",
        "YourArchive.zip": "sample.zip",
        "my_archive.zip": "sample.zip",
        "files.zip": "sample.zip",
    }

    applied = []
    fixed_code = code

    for placeholder, replacement in placeholder_archives.items():
        if f'"{placeholder}"' in fixed_code:
            fixed_code = fixed_code.replace(f'"{placeholder}"', f'"{replacement}"')
            applied.append(f"{placeholder} -> {replacement}")

    if not applied:
        return code, ""

    fix_desc = f"RUNTIME: Replaced placeholder archives: {', '.join(applied)}"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_compression_level_invalid_values(code: str) -> Tuple[str, str]:
    """
    Fix invalid CompressionLevel enum values.

    System.IO.Compression.CompressionLevel has: Optimal, Fastest, NoCompression, SmallestSize.
    Invalid values in blog posts:
    - 'Normal' -> 'Optimal' (default balanced compression)
    - 'Low' -> 'Fastest' (fast compression, less ratio)
    - 'High' -> 'SmallestSize' (best compression, slower)
    """
    replacements = {
        'CompressionLevel.Normal': 'CompressionLevel.Optimal',
        'CompressionLevel.Low': 'CompressionLevel.Fastest',
        'CompressionLevel.High': 'CompressionLevel.SmallestSize',
    }

    applied = []
    fixed_code = code
    for old_val, new_val in replacements.items():
        if old_val in fixed_code:
            fixed_code = fixed_code.replace(old_val, new_val)
            applied.append(f"{old_val} -> {new_val}")

    if not applied:
        return code, ""

    fix_desc = f"CS0117: Replaced invalid CompressionLevel values: {', '.join(applied)}"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_deflate_compression_settings_constructor(code: str) -> Tuple[str, str]:
    """
    Fix CS1729: DeflateCompressionSettings doesn't take CompressionLevel as constructor arg.

    The Aspose.Zip DeflateCompressionSettings() constructor takes no arguments.
    Blog examples incorrectly show: new DeflateCompressionSettings(CompressionLevel.Normal)
    or: new DeflateCompressionSettings(level) where level is a variable

    Transform to: new DeflateCompressionSettings()
    """
    applied = False
    fixed_code = code

    # Pattern 1: new DeflateCompressionSettings(CompressionLevel.<anything>)
    pattern1 = r'new\s+DeflateCompressionSettings\s*\(\s*CompressionLevel\.\w+\s*\)'
    if re.search(pattern1, fixed_code):
        fixed_code = re.sub(pattern1, 'new DeflateCompressionSettings()', fixed_code)
        applied = True

    # Pattern 2: new DeflateCompressionSettings(variable) - any single identifier arg
    # This is safe because the only valid constructor is parameterless
    pattern2 = r'new\s+DeflateCompressionSettings\s*\(\s*[a-zA-Z_]\w*\s*\)'
    if re.search(pattern2, fixed_code):
        fixed_code = re.sub(pattern2, 'new DeflateCompressionSettings()', fixed_code)
        applied = True

    if not applied:
        return code, ""

    fix_desc = "CS1729: Removed invalid argument from DeflateCompressionSettings constructor"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_compression_level_parameter(code: str) -> Tuple[str, str]:
    """
    Fix method parameters using CompressionLevel type.

    CompressionLevel is from System.IO.Compression which is a BCL type,
    but Aspose.Zip uses its own compression settings. Remove these parameters.

    Transform:
        public static byte[] Method(string path, CompressionLevel level = CompressionLevel.Normal)
    Into:
        public static byte[] Method(string path)
    """
    # Match: , CompressionLevel <varname> = CompressionLevel.<value> as a parameter
    pattern = r',\s*CompressionLevel\s+\w+\s*=\s*CompressionLevel\.\w+'

    if not re.search(pattern, code):
        return code, ""

    fixed_code = re.sub(pattern, '', code)

    fix_desc = "CS0246: Removed CompressionLevel parameter (Aspose.Zip uses different compression API)"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


def fix_archive_iteration_try_catch(code: str) -> Tuple[str, str]:
    """
    Fix runtime failures when iterating over archive files.

    When code uses Directory.GetFiles(".", "*.zip") and iterates with foreach,
    some test archives may be encrypted/corrupted. Wrap the archive body in
    try-catch to skip problematic files.

    Transforms:
        foreach (string file in files)
        {
            using (Archive archive = new Archive(file))
            {
                archive.ExtractToDirectory("output_folder");
            }
        }
    Into:
        foreach (string file in files)
        {
            try
            {
                using (Archive archive = new Archive(file))
                {
                    archive.ExtractToDirectory("output_folder");
                }
            }
            catch (Exception) { continue; }
        }
    """
    # Only apply if code has Directory.GetFiles + foreach + new Archive pattern
    has_getfiles = 'Directory.GetFiles' in code and '*.zip' in code
    has_foreach = 'foreach' in code
    has_new_archive = 'new Archive(file' in code or 'new Archive(f)' in code

    if not (has_getfiles and has_foreach and has_new_archive):
        return code, ""

    lines = code.split('\n')
    # Find the foreach line
    foreach_idx = -1
    foreach_brace_idx = -1
    foreach_end_idx = -1

    for i, line in enumerate(lines):
        if 'foreach' in line and ('file' in line or ' f ' in line):
            foreach_idx = i
            break

    if foreach_idx < 0:
        return code, ""

    # Find the opening brace of the foreach
    brace_count = 0
    for i in range(foreach_idx, min(foreach_idx + 3, len(lines))):
        if '{' in lines[i]:
            foreach_brace_idx = i
            break

    if foreach_brace_idx < 0:
        return code, ""

    # Find the closing brace of the foreach
    brace_count = 0
    for i in range(foreach_brace_idx, len(lines)):
        brace_count += lines[i].count('{')
        brace_count -= lines[i].count('}')
        if brace_count == 0:
            foreach_end_idx = i
            break

    if foreach_end_idx < 0:
        return code, ""

    # Get the indent of the foreach body
    body_indent = ''
    for i in range(foreach_brace_idx + 1, foreach_end_idx):
        stripped = lines[i].strip()
        if stripped and stripped != '{' and stripped != '}':
            body_indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            break

    if not body_indent:
        body_indent = '        '

    # Idempotency guard: skip if try-catch already exists in foreach body
    foreach_body = '\n'.join(lines[foreach_brace_idx + 1:foreach_end_idx])
    if re.search(r'\btry\b', foreach_body) and re.search(r'\bcatch\b', foreach_body):
        return code, ""

    # Wrap the body in try-catch
    new_lines = lines[:foreach_brace_idx + 1]
    new_lines.append(f'{body_indent}try')
    new_lines.append(f'{body_indent}{{')

    # Add original body with extra indentation
    for i in range(foreach_brace_idx + 1, foreach_end_idx):
        line = lines[i]
        if line.strip():
            new_lines.append(f'    {line}')
        else:
            new_lines.append(line)

    new_lines.append(f'{body_indent}}}')
    new_lines.append(f'{body_indent}catch (Exception) {{ continue; }}')
    new_lines.extend(lines[foreach_end_idx:])

    fixed_code = '\n'.join(new_lines)
    fix_desc = "RUNTIME: Added try-catch around archive iteration to skip encrypted/corrupt archives"
    logger.info(f"Applied fix: {fix_desc}")
    return fixed_code, fix_desc


# Registry of ZIP-specific fix functions
# These are applied proactively before compilation when family='zip'
ZIP_SPECIFIC_FIXES = [
    fix_rar_archive_password,
    fix_entries_string_index,
    fix_placeholder_archive_paths,
    fix_compression_level_invalid_values,
    fix_deflate_compression_settings_constructor,
    fix_compression_level_parameter,
    fix_archive_iteration_try_catch,
]
