"""Test API parser regex patterns."""

import re
import sys
from pathlib import Path

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Read the Archive.md file
file_path = r"D:\onedrive\Documents\GitHub\aspose.net\content\reference.aspose.net\zip\en\Aspose.Zip.Archive.md"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("File loaded, size:", len(content))
print("\n" + "="*80)

# Test 1: Find Constructors section
ctor_section = re.search(r'## Constructors\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
if ctor_section:
    print("\n[OK] Found Constructors section")
    print(f"Section length: {len(ctor_section.group(1))}")
    print(f"First 200 chars:\n{ctor_section.group(1)[:200]}")
else:
    print("\n[FAIL] Constructors section not found")

print("\n" + "="*80)

# Test 2: Find constructor entries
if ctor_section:
    # CORRECTED pattern - text is AFTER </a>, not inside <a>...</a>
    ctor_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'
    matches = list(re.finditer(ctor_pattern, ctor_section.group(1), re.DOTALL))
    print(f"\n[OK] Found {len(matches)} constructors with CORRECTED pattern")

    if matches:
        for i, match in enumerate(matches[:2], 1):  # Show first 2
            print(f"\nConstructor {i}:")
            print(f"  Name: {match.group(1).strip()}")
            print(f"  Description: {match.group(2).strip()[:50]}...")
            print(f"  Signature: {match.group(3).strip()[:80]}")
    else:
        # Try simplest pattern to find headers
        simple_pattern = r'### <a[^>]*></a> (.+?)(?=\n)'
        simple_matches = re.findall(simple_pattern, ctor_section.group(1))
        print(f"\n  Found {len(simple_matches)} constructor headers:")
        for sm in simple_matches[:5]:
            print(f"    - {sm}")

        # Check what's between header and code
        print("\n  Checking content after first header:")
        first_header = re.search(r'### <a[^>]*>([^<]+)</a>\n\n', ctor_section.group(1))
        if first_header:
            after_header = ctor_section.group(1)[first_header.end():first_header.end()+200]
            print(f"    {repr(after_header)}")

print("\n" + "="*80)

# Test 3: Find Methods section
method_section = re.search(r'## Methods\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
if method_section:
    print("\n[OK] Found Methods section")
    print(f"Section length: {len(method_section.group(1))}")

    # CORRECTED pattern
    method_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'
    method_matches = list(re.finditer(method_pattern, method_section.group(1), re.DOTALL))
    print(f"[OK] Found {len(method_matches)} methods with CORRECTED pattern")

    if method_matches:
        for i, match in enumerate(method_matches[:2], 1):
            print(f"\nMethod {i}:")
            print(f"  Name: {match.group(1)}")
            print(f"  Signature: {match.group(3).strip()[:80]}")
else:
    print("\n[FAIL] Methods section not found")

print("\n" + "="*80)

# Test 4: Find Properties section
prop_section = re.search(r'## Properties\n\n(.+?)(?=\n## |$)', content, re.DOTALL)
if prop_section:
    print("\n[OK] Found Properties section")
    print(f"Section length: {len(prop_section.group(1))}")

    # CORRECTED pattern
    prop_pattern = r'### <a[^>]*></a> (.+?)\n\n(.+?)\n\n```csharp\n(.+?)```'
    prop_matches = list(re.finditer(prop_pattern, prop_section.group(1), re.DOTALL))
    print(f"[OK] Found {len(prop_matches)} properties with CORRECTED pattern")

    if prop_matches:
        for i, match in enumerate(prop_matches[:2], 1):
            print(f"\nProperty {i}:")
            print(f"  Name: {match.group(1)}")
            print(f"  Signature: {match.group(3).strip()}")
else:
    print("\n[FAIL] Properties section not found")

print("\n" + "="*80)
print("\nDone!")
