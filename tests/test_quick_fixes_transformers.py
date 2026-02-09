"""
Tests for E2 Enhanced Transformers in apply_quick_fixes()

Tests each of the 4 new transformers:
1. System.IO.Compression Ban Transformer
2. Known Hallucination Patterns Transformer
3. Async-to-Sync Normalization Transformer
4. Path Handling Fixes Transformer
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.example_substitution_service import apply_quick_fixes


class TestSystemIOCompressionBan(unittest.TestCase):
    """Test System.IO.Compression Ban Transformer"""

    def test_remove_system_io_compression_and_add_aspose_zip(self):
        """Should remove System.IO.Compression and add Aspose.Zip"""
        code = """using System;
using System.IO.Compression;

class Program {
    static void Main() {
        Console.WriteLine("Test");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should remove System.IO.Compression
        self.assertNotIn('using System.IO.Compression;', fixed)

        # Should add Aspose.Zip
        self.assertIn('using Aspose.Zip;', fixed)

        # Should log the fix
        self.assertIn('system_io_compression_ban', fixes)

    def test_already_has_aspose_zip(self):
        """Should not duplicate Aspose.Zip if already present"""
        code = """using System;
using System.IO.Compression;
using Aspose.Zip;

class Program {
    static void Main() {
        Console.WriteLine("Test");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should only have one Aspose.Zip using
        self.assertEqual(fixed.count('using Aspose.Zip;'), 1)
        self.assertIn('system_io_compression_ban', fixes)


class TestKnownHallucinationPatterns(unittest.TestCase):
    """Test Known Hallucination Patterns Transformer"""

    def test_comment_out_ziparchivemode(self):
        """Should comment out ZipArchiveMode usage"""
        code = """using System;

class Program {
    static void Main() {
        var mode = ZipArchiveMode.Create;
        Console.WriteLine("Test");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should comment out the line
        self.assertIn('// REMOVED: ZipArchiveMode is not available in Aspose.Zip API', fixed)
        self.assertIn('// var mode = ZipArchiveMode.Create;', fixed)

        # Should log the fix
        self.assertTrue(any('hallucination_fix' in f for f in fixes))

    def test_comment_out_zipfile_openread(self):
        """Should comment out ZipFile.OpenRead usage"""
        code = """using System;

class Program {
    static void Main() {
        var archive = ZipFile.OpenRead("test.zip");
        Console.WriteLine("Test");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should comment out the line
        self.assertIn('// REMOVED: ZipFile.OpenRead is not available in Aspose.Zip API', fixed)
        self.assertIn('// var archive = ZipFile.OpenRead("test.zip");', fixed)

        # Should log the fix
        self.assertTrue(any('hallucination_fix' in f for f in fixes))

    def test_comment_out_zipfile_createfromdirectory(self):
        """Should comment out ZipFile.CreateFromDirectory usage"""
        code = """using System;

class Program {
    static void Main() {
        ZipFile.CreateFromDirectory("source", "output.zip");
        Console.WriteLine("Test");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should comment out the line
        self.assertIn('// REMOVED: ZipFile.CreateFromDirectory is not available in Aspose.Zip API', fixed)
        self.assertIn('// ZipFile.CreateFromDirectory("source", "output.zip");', fixed)

        # Should log the fix
        self.assertTrue(any('hallucination_fix' in f for f in fixes))

    def test_add_aspose_zip_after_hallucination_fix(self):
        """Should add Aspose.Zip using after fixing hallucinations"""
        code = """using System;

class Program {
    static void Main() {
        var mode = ZipArchiveMode.Create;
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should add Aspose.Zip
        self.assertIn('using Aspose.Zip;', fixed)


class TestAsyncToSyncNormalization(unittest.TestCase):
    """Test Async-to-Sync Normalization Transformer"""

    def test_convert_async_task_main_to_void_main(self):
        """Should convert async Task Main to void Main when no await is used"""
        code = """using System;
using System.Threading.Tasks;

class Program {
    static async Task Main(string[] args) {
        Console.WriteLine("No await here");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should convert to void Main
        self.assertIn('static void Main(string[] args)', fixed)
        self.assertNotIn('async Task Main', fixed)

        # Should log the fix
        self.assertIn('async_to_sync_normalization', fixes)

    def test_keep_async_main_with_await(self):
        """Should keep async Task Main when await is used"""
        code = """using System;
using System.Threading.Tasks;

class Program {
    static async Task Main(string[] args) {
        await Task.Delay(100);
        Console.WriteLine("Has await");
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should keep async Task Main
        self.assertIn('async Task Main', fixed)

        # Should not log the fix
        self.assertNotIn('async_to_sync_normalization', fixes)

    def test_convert_async_task_int_main(self):
        """Should convert async Task<int> Main to int Main when no await is used"""
        code = """using System;
using System.Threading.Tasks;

class Program {
    static async Task<int> Main(string[] args) {
        Console.WriteLine("No await here");
        return 0;
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should convert to int Main
        self.assertIn('static int Main(string[] args)', fixed)
        self.assertNotIn('async Task<int> Main', fixed)

        # Should log the fix
        self.assertIn('async_to_sync_normalization', fixes)


class TestPathHandlingFixes(unittest.TestCase):
    """Test Path Handling Fixes Transformer"""

    def test_replace_windows_path_with_path_combine(self):
        """Should replace hardcoded Windows path with Path.Combine"""
        code = """using System;

class Program {
    static void Main() {
        var path = "C:\\temp\\output";
        Console.WriteLine(path);
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should replace with Path.Combine
        self.assertIn('Path.Combine("C:", "temp", "output")', fixed)
        self.assertNotIn('"C:\\\\temp\\\\output"', fixed)

        # Should add System.IO using
        self.assertIn('using System.IO;', fixed)

        # Should log the fix
        self.assertIn('path_handling_fixes', fixes)

    def test_multiple_windows_paths(self):
        """Should replace multiple Windows paths"""
        code = """using System;

class Program {
    static void Main() {
        var path1 = "C:\\data\\input";
        var path2 = "D:\\output\\results";
        Console.WriteLine(path1 + path2);
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should replace both paths
        self.assertIn('Path.Combine("C:", "data", "input")', fixed)
        self.assertIn('Path.Combine("D:", "output", "results")', fixed)

        # Should log the fix
        self.assertIn('path_handling_fixes', fixes)

    def test_skip_file_paths(self):
        """Should not replace paths that end with file extensions"""
        code = """using System;

class Program {
    static void Main() {
        var file = "test.zip";
        Console.WriteLine(file);
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should not apply path handling fix for file names
        self.assertNotIn('path_handling_fixes', fixes)

    def test_already_has_system_io(self):
        """Should not duplicate System.IO if already present"""
        code = """using System;
using System.IO;

class Program {
    static void Main() {
        var path = "C:\\temp\\output";
        Console.WriteLine(path);
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should only have one System.IO using
        self.assertEqual(fixed.count('using System.IO;'), 1)
        self.assertIn('path_handling_fixes', fixes)


class TestCombinedTransformers(unittest.TestCase):
    """Test multiple transformers working together"""

    def test_multiple_fixes_applied(self):
        """Should apply multiple fixes in one pass"""
        code = """using System;
using System.IO.Compression;

class Program {
    static async Task Main(string[] args) {
        var mode = ZipArchiveMode.Create;
        var path = "C:\\temp\\output";
        Console.WriteLine(path);
    }
}"""
        fixed, fixes = apply_quick_fixes(code, [])

        # Should apply System.IO.Compression ban
        self.assertIn('system_io_compression_ban', fixes)
        self.assertNotIn('using System.IO.Compression;', fixed)

        # Should apply hallucination fix
        self.assertTrue(any('hallucination_fix' in f for f in fixes))
        self.assertIn('// REMOVED: ZipArchiveMode', fixed)

        # Should apply async-to-sync
        self.assertIn('async_to_sync_normalization', fixes)
        self.assertIn('static void Main(string[] args)', fixed)

        # Should apply path handling
        self.assertIn('path_handling_fixes', fixes)
        self.assertIn('Path.Combine', fixed)


if __name__ == '__main__':
    unittest.main()
