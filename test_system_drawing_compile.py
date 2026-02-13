#!/usr/bin/env python3
"""
Test script to verify System.Drawing.Common package functionality
by compiling test files using the project's compilation infrastructure.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.compilation_service import CompilationService
from models.family_config import FamilyConfig
import json

def test_compilation(test_name, code):
    """Test if code compiles successfully."""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")

    # Use words family config since that's what example 757969e9 uses
    family_config = FamilyConfig(
        name="words",
        default_usings=[
            "System",
            "System.IO",
            "System.Drawing",
            "System.Drawing.Printing",
            "System.Drawing.Imaging",
            "System.Drawing.Drawing2D"
        ],
        required_packages={
            "Aspose.Words": "*",
            "System.Drawing.Common": "8.0.0"
        },
        test_data_path="",
        required_dirs=[],
        required_files=[],
        api_catalog=None,
        fixture_passwords=None
    )

    service = CompilationService()
    result = service.compile_example(
        example_id=f"test_{test_name}",
        family="words",
        code=code,
        family_config=family_config,
        timeout=30
    )

    print(f"Success: {result.success}")
    if not result.success:
        print(f"Errors: {result.errors}")
    else:
        print("✓ Compilation succeeded!")

    return result.success

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    tests = {
        "basic_drawing": """
using System;
using System.Drawing;

namespace Test {
    class Program {
        static void Main() {
            Color c = Color.Red;
            Point p = new Point(10, 20);
            Console.WriteLine("Basic Drawing types work!");
        }
    }
}
""",
        "printing": """
using System;
using System.Drawing.Printing;

namespace Test {
    class Program {
        static void Main() {
            PrinterSettings settings = new PrinterSettings();
            PageSettings page = new PageSettings();
            Console.WriteLine("Printing types work!");
        }
    }
}
""",
        "imaging": """
using System;
using System.Drawing.Imaging;

namespace Test {
    class Program {
        static void Main() {
            ImageFormat fmt = ImageFormat.Png;
            Console.WriteLine("Imaging types work!");
        }
    }
}
""",
        "drawing2d": """
using System;
using System.Drawing;
using System.Drawing.Drawing2D;

namespace Test {
    class Program {
        static void Main() {
            GraphicsPath path = new GraphicsPath();
            Matrix m = new Matrix();
            Console.WriteLine("Drawing2D types work!");
        }
    }
}
"""
    }

    results = {}
    for name, code in tests.items():
        results[name] = test_compilation(name, code)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {sum(results.values())}/{len(results)} passed")
