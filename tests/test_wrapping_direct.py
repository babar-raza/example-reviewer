#!/usr/bin/env python3
"""
Direct test of the code wrapping functionality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.config import ConfigurationManager
from core.database import Database
from services.compilation_service import CompilationService
from core.models import ExampleRecord

def test_wrapping():
    print("="*70)
    print("  DIRECT CODE WRAPPING TEST")
    print("="*70)

    # Initialize services
    config_manager = ConfigurationManager(Path('config/families'))
    zip_config = config_manager.load_family_config('zip')
    db = Database(Path('data/test_wrapping.db'))
    db.initialize_schema()

    compilation_service = CompilationService(
        db,
        workspace_dir=Path('workspace/test_wrapping'),
        artifacts_dir=Path('artifacts/test_wrapping')
    )

    # Test cases from the actual failures
    test_cases = [
        {
            "name": "Example with comments",
            "code": """using System;
using System.IO;
using Aspose.Zip;

// Open the ZIP archive
using (var archive = new Archive("sample.zip"))
{
    // Extract all entries to a directory
    archive.ExtractToDirectory("output");
}"""
        },
        {
            "name": "RarArchive without using",
            "code": """using (RarArchive archive = new RarArchive("input.rar"))
{
    RarArchiveEntry entry = archive.Entries["example.txt"];
    entry.Extract("output_folder/example.txt");
}"""
        },
        {
            "name": "Code with existing class",
            "code": """using Aspose.Zip;

public class ZipExample
{
    public void ProcessZip()
    {
        var archive = new Archive("test.zip");
        archive.ExtractToDirectory("output");
    }
}"""
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test['name']}")
        print('='*70)

        code = test['code']
        print(f"\nOriginal code ({len(code)} chars):")
        print(code[:200] + "..." if len(code) > 200 else code)

        # Analyze the code
        analysis = compilation_service._analyze_code(code, zip_config)
        print(f"\nAnalysis:")
        print(f"  Has usings: {analysis['has_usings']}")
        print(f"  Has class: {analysis['has_class']}")
        print(f"  Has Main: {analysis['has_main']}")
        print(f"  Is async: {analysis['is_async']}")
        print(f"  Detected APIs: {analysis['detected_apis']}")
        print(f"  Missing usings: {analysis['missing_usings']}")

        # Wrap the code
        wrapped = compilation_service._wrap_code(code, zip_config)
        print(f"\nWrapped code ({len(wrapped)} chars):")
        print(wrapped)

        # Try to compile it
        example = ExampleRecord(
            family="zip",
            file_path="/test/example.md",
            original_code=code,
        )

        print(f"\nCompiling...")
        success, result = compilation_service.compile_example(example, zip_config)

        if success:
            print(f"SUCCESS - Compiled in {result.duration_ms}ms")
        else:
            print(f"FAILED - Compilation errors:")
            for err in result.errors[:3]:
                print(f"  - {err[:150]}")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    test_wrapping()
