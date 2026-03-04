"""
Generate initial test fixtures for Aspose.BarCode examples.
"""
import os
import subprocess
import sys
from pathlib import Path

# CRITICAL: Configure UTF-8 encoding for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
TEST_DATA_DIR = REPO_ROOT / "artifacts" / "backfill" / "barcode" / "test-data"
TEMP_CS_FILE = REPO_ROOT / "test-examples" / "generate_barcode_test_data.cs"

# C# code to generate barcode fixtures
GENERATOR_CODE = """
using System;
using System.IO;
using Aspose.BarCode.Generation;

class BarcodeFixtureGenerator
{
    static void Main(string[] args)
    {
        string outputDir = args[0];
        Directory.CreateDirectory(outputDir);

        // Generate basic barcode images
        Console.WriteLine("Generating barcode fixtures...");

        // Sample barcode (Code128)
        using (var generator = new BarcodeGenerator(EncodeTypes.Code128, "SAMPLE123"))
        {
            generator.Parameters.Barcode.XDimension.Millimeters = 1f;
            generator.Save(Path.Combine(outputDir, "sample.png"), BarCodeImageFormat.Png);
        }

        // Barcode.png (QR Code)
        using (var generator = new BarcodeGenerator(EncodeTypes.QR, "https://aspose.com"))
        {
            generator.Parameters.Barcode.XDimension.Millimeters = 2f;
            generator.Save(Path.Combine(outputDir, "barcode.png"), BarCodeImageFormat.Png);
        }

        // Test.png (DataMatrix)
        using (var generator = new BarcodeGenerator(EncodeTypes.DataMatrix, "TEST-DATA"))
        {
            generator.Parameters.Barcode.XDimension.Millimeters = 1.5f;
            generator.Save(Path.Combine(outputDir, "test.png"), BarCodeImageFormat.Png);
        }

        // Additional common formats
        using (var generator = new BarcodeGenerator(EncodeTypes.Code39Standard, "ABC123"))
        {
            generator.Save(Path.Combine(outputDir, "code39.png"), BarCodeImageFormat.Png);
        }

        using (var generator = new BarcodeGenerator(EncodeTypes.EAN13, "1234567890128"))
        {
            generator.Save(Path.Combine(outputDir, "ean13.png"), BarCodeImageFormat.Png);
        }

        Console.WriteLine($"Generated 5 barcode fixture files in {outputDir}");
    }
}
"""

def main():
    print(f"Generating BarCode test fixtures...")
    print(f"Output directory: {TEST_DATA_DIR}")

    # Write temporary C# file
    TEMP_CS_FILE.write_text(GENERATOR_CODE, encoding='utf-8')

    try:
        # Compile and run
        cmd = [
            "dotnet", "script", str(TEMP_CS_FILE),
            "--", str(TEST_DATA_DIR)
        ]

        # Alternative: use csi or dotnet build+run
        # Let's use a simpler approach: add to test-examples and build inline
        compile_cmd = [
            "dotnet", "build", str(REPO_ROOT / "test-examples"),
            "-c", "Release"
        ]

        print("Building test-examples project...")
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Build failed: {result.stderr}")
            return 1

        # Create a standalone runner
        runner_path = REPO_ROOT / "test-examples" / "barcode_fixture_gen.csproj"
        runner_cs = REPO_ROOT / "test-examples" / "barcode_fixture_gen.cs"

        # Create minimal csproj
        csproj_content = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Aspose.BarCode" Version="26.1.0" />
  </ItemGroup>
</Project>"""

        runner_path.write_text(csproj_content, encoding='utf-8')
        runner_cs.write_text(GENERATOR_CODE, encoding='utf-8')

        # Build and run
        print("Building fixture generator...")
        build_result = subprocess.run(
            ["dotnet", "build", str(runner_path), "-c", "Release"],
            capture_output=True, text=True, cwd=str(REPO_ROOT / "test-examples")
        )

        if build_result.returncode != 0:
            print(f"Build error: {build_result.stderr}")
            return 1

        print("Running fixture generator...")
        run_result = subprocess.run(
            ["dotnet", "run", "--project", str(runner_path), "--", str(TEST_DATA_DIR)],
            capture_output=True, text=True, cwd=str(REPO_ROOT / "test-examples")
        )

        print(run_result.stdout)
        if run_result.returncode != 0:
            print(f"Runtime error: {run_result.stderr}")
            return 1

        # Cleanup
        runner_path.unlink()
        runner_cs.unlink()
        (REPO_ROOT / "test-examples" / "obj").rmdir() if (REPO_ROOT / "test-examples" / "obj").exists() else None

        print("\nFixture generation complete!")
        return 0

    finally:
        # Cleanup temp file
        if TEMP_CS_FILE.exists():
            TEMP_CS_FILE.unlink()

if __name__ == "__main__":
    sys.exit(main())
