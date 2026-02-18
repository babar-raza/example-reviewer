"""
Demonstration of E2 Enhanced Transformers

This script demonstrates each of the 4 new transformers:
1. System.IO.Compression Ban Transformer
2. Known Hallucination Patterns Transformer
3. Async-to-Sync Normalization Transformer
4. Path Handling Fixes Transformer
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.example_substitution_service import apply_quick_fixes


def demo_transformer(name, description, code, errors=None):
    """Demonstrate a transformer"""
    print(f"\n{'='*80}")
    print(f"TRANSFORMER: {name}")
    print(f"{'='*80}")
    print(f"\nDescription: {description}\n")
    print("BEFORE:")
    print("-" * 80)
    print(code)
    print("-" * 80)

    fixed, fixes = apply_quick_fixes(code, errors or [])

    print("\nAFTER:")
    print("-" * 80)
    print(fixed)
    print("-" * 80)
    print(f"\nApplied fixes: {', '.join(fixes) if fixes else 'None'}")


def main():
    print("E2 Enhanced Transformers Demonstration")
    print("=" * 80)

    # Demo 1: System.IO.Compression Ban
    demo_transformer(
        "System.IO.Compression Ban",
        "Removes System.IO.Compression and adds Aspose.Zip",
        """using System;
using System.IO.Compression;

class Program {
    static void Main() {
        Console.WriteLine("Creating zip archive");
    }
}"""
    )

    # Demo 2: Known Hallucination Patterns
    demo_transformer(
        "Known Hallucination Patterns",
        "Comments out ZipArchiveMode, ZipFile.OpenRead, ZipFile.CreateFromDirectory",
        """using System;

class Program {
    static void Main() {
        var mode = ZipArchiveMode.Create;
        var archive = ZipFile.OpenRead("test.zip");
        ZipFile.CreateFromDirectory("source", "output.zip");
    }
}"""
    )

    # Demo 3: Async-to-Sync Normalization
    demo_transformer(
        "Async-to-Sync Normalization",
        "Converts unnecessary async Task Main to void Main",
        """using System;
using System.Threading.Tasks;

class Program {
    static async Task Main(string[] args) {
        Console.WriteLine("No async operations here");
        var x = 42;
    }
}"""
    )

    # Demo 4: Path Handling Fixes
    demo_transformer(
        "Path Handling Fixes",
        "Replaces hardcoded Windows paths with Path.Combine",
        """using System;

class Program {
    static void Main() {
        var inputPath = "C:\\data\\input";
        var outputPath = "D:\\output\\results";
        Console.WriteLine(inputPath + " -> " + outputPath);
    }
}"""
    )

    # Demo 5: Combined Transformers
    demo_transformer(
        "Combined Transformers (All 4)",
        "All transformers working together on complex code",
        """using System;
using System.IO.Compression;
using System.Threading.Tasks;

class Program {
    static async Task Main(string[] args) {
        var mode = ZipArchiveMode.Create;
        var path = "C:\\temp\\archives";
        ZipFile.CreateFromDirectory(path, "output.zip", mode, false);
        Console.WriteLine("Done");
    }
}"""
    )

    print(f"\n{'='*80}")
    print("Demonstration Complete!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
