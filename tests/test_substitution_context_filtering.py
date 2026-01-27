"""
Tests for context-aware substitution filtering.

Tests that ExampleSubstitutionService respects same_context_only flag
and prevents cross-context substitution (e.g., ASP.NET → console).
"""

import pytest
import tempfile
import json
from pathlib import Path
from src.services.example_substitution_service import ExampleSubstitutionService


class TestSubstitutionContextFiltering:
    """Test context filtering in substitution service."""

    def create_test_index(self, tmp_path: Path, examples: list) -> Path:
        """Helper to create a test examples-index.json"""
        backfill_dir = tmp_path / "backfill"
        backfill_dir.mkdir(parents=True, exist_ok=True)

        index_data = {"examples": examples}

        index_path = backfill_dir / "examples-index.json"
        with open(index_path, 'w') as f:
            json.dump(index_data, f)

        # Create example files
        examples_dir = backfill_dir / "examples"
        examples_dir.mkdir(parents=True, exist_ok=True)

        for example in examples:
            ex_path = examples_dir / example['path']
            ex_path.parent.mkdir(parents=True, exist_ok=True)
            with open(ex_path, 'w') as f:
                f.write(example.get('code', '// placeholder'))

        return backfill_dir

    def test_substitution_with_flag_disabled_allows_cross_context(self, tmp_path):
        """Test that cross-context substitution works when flag is disabled (default)"""
        # Create test index with mixed contexts
        examples = [
            {
                'id': 'console_example',
                'path': 'Examples/ConsoleExample.cs',
                'class_name': 'ConsoleExample',
                'tags': ['zip', 'archive'],
                'size_bytes': 500,
                'code': 'using Aspose.Zip;\nvar archive = new Archive();\narchive.Save("output.zip");'
            },
            {
                'id': 'aspnet_example',
                'path': 'Examples/AspNetExample.cs',
                'class_name': 'AspNetExample',
                'tags': ['zip', 'archive'],
                'size_bytes': 600,
                'code': 'var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\napp.MapGet("/", () => "Hello");\napp.Run();'
            }
        ]

        backfill_dir = self.create_test_index(tmp_path, examples)

        # Initialize service with flag DISABLED (default)
        service = ExampleSubstitutionService(backfill_dir, same_context_only=False)

        # Simulate ASP.NET code with compile error
        original_code = 'var builder = WebApplication.CreateBuilder(args);'
        trigger_info = {'keywords': ['zip', 'archive'], 'avoid_classes': [], 'reason': 'test'}

        # Should find substitute even if context doesn't match
        result = service.find_substitute_example(
            original_code=original_code,
            trigger_info=trigger_info,
            family='zip',
            original_app_context='aspnet_core_minimal'
        )

        assert result is not None, "Should find substitute when flag is disabled"
        substitute_code, example_id, metadata = result
        # Could be either console or aspnet example (no filtering)
        assert example_id in ['console_example', 'aspnet_example']

    def test_substitution_with_flag_enabled_blocks_cross_context(self, tmp_path):
        """Test that cross-context substitution is blocked when flag is enabled"""
        # Create test index with only console examples
        examples = [
            {
                'id': 'console_example1',
                'path': 'Examples/Console1.cs',
                'class_name': 'Console1',
                'tags': ['zip', 'archive'],
                'size_bytes': 500,
                'code': 'using Aspose.Zip;\nvar archive = new Archive();\narchive.Save("output.zip");'
            },
            {
                'id': 'console_example2',
                'path': 'Examples/Console2.cs',
                'class_name': 'Console2',
                'tags': ['zip', 'compress'],
                'size_bytes': 400,
                'code': 'using System;\nusing Aspose.Zip;\nvar arch = new Archive();\narch.CreateEntry("file.txt", "data.txt");'
            }
        ]

        backfill_dir = self.create_test_index(tmp_path, examples)

        # Initialize service with flag ENABLED
        service = ExampleSubstitutionService(backfill_dir, same_context_only=True)

        # Simulate ASP.NET code with compile error
        original_code = 'var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();'
        trigger_info = {'keywords': ['zip', 'archive'], 'avoid_classes': [], 'reason': 'test'}

        # Should NOT find substitute because all candidates are console context
        result = service.find_substitute_example(
            original_code=original_code,
            trigger_info=trigger_info,
            family='zip',
            original_app_context='aspnet_core_minimal'
        )

        assert result is None, "Should NOT find substitute when context doesn't match and flag is enabled"

    def test_substitution_with_matching_context_succeeds(self, tmp_path):
        """Test that substitution works when contexts match"""
        examples = [
            {
                'id': 'console_example',
                'path': 'Examples/ConsoleExample.cs',
                'class_name': 'ConsoleExample',
                'tags': ['zip', 'archive'],
                'size_bytes': 500,
                'code': 'using Aspose.Zip;\nvar archive = new Archive();\narchive.Save("output.zip");'
            },
            {
                'id': 'aspnet_example',
                'path': 'Examples/AspNetExample.cs',
                'class_name': 'AspNetExample',
                'tags': ['zip', 'archive'],
                'size_bytes': 600,
                'code': 'var builder = WebApplication.CreateBuilder(args);\nvar app = builder.Build();\nvar archive = new Archive();\napp.Run();'
            }
        ]

        backfill_dir = self.create_test_index(tmp_path, examples)

        # Initialize service with flag ENABLED
        service = ExampleSubstitutionService(backfill_dir, same_context_only=True)

        # Simulate ASP.NET code with compile error
        original_code = 'var builder = WebApplication.CreateBuilder(args);'
        trigger_info = {'keywords': ['zip', 'archive'], 'avoid_classes': [], 'reason': 'test'}

        # Should find the ASP.NET example (context matches)
        result = service.find_substitute_example(
            original_code=original_code,
            trigger_info=trigger_info,
            family='zip',
            original_app_context='aspnet_core_minimal'
        )

        assert result is not None, "Should find substitute when context matches"
        substitute_code, example_id, metadata = result
        assert example_id == 'aspnet_example', "Should prefer context-matched example"
        assert 'WebApplication' in substitute_code

    def test_substitution_without_app_context_parameter_works(self, tmp_path):
        """Test that service works when original_app_context is not provided"""
        examples = [
            {
                'id': 'console_example',
                'path': 'Examples/ConsoleExample.cs',
                'class_name': 'ConsoleExample',
                'tags': ['zip', 'archive'],
                'size_bytes': 500,
                'code': 'using Aspose.Zip;\nvar archive = new Archive();'
            }
        ]

        backfill_dir = self.create_test_index(tmp_path, examples)

        # Flag enabled but no app_context provided
        service = ExampleSubstitutionService(backfill_dir, same_context_only=True)

        original_code = 'var archive = new Archive();'
        trigger_info = {'keywords': ['zip', 'archive'], 'avoid_classes': [], 'reason': 'test'}

        # Should still find substitute (context check skipped when original_app_context is None)
        result = service.find_substitute_example(
            original_code=original_code,
            trigger_info=trigger_info,
            family='zip',
            original_app_context=None  # Not provided
        )

        assert result is not None, "Should find substitute when app_context not provided"

    def test_substitution_prefers_smaller_examples_within_same_context(self, tmp_path):
        """Test that smaller examples are preferred when multiple candidates match context"""
        examples = [
            {
                'id': 'large_console',
                'path': 'Examples/Large.cs',
                'class_name': 'Large',
                'tags': ['zip', 'archive'],
                'size_bytes': 1000,
                'code': 'using Aspose.Zip;\n' + ('// filler line\n' * 50) + 'var archive = new Archive();'
            },
            {
                'id': 'small_console',
                'path': 'Examples/Small.cs',
                'class_name': 'Small',
                'tags': ['zip', 'archive'],
                'size_bytes': 200,
                'code': 'using Aspose.Zip;\nvar archive = new Archive();'
            }
        ]

        backfill_dir = self.create_test_index(tmp_path, examples)

        service = ExampleSubstitutionService(backfill_dir, same_context_only=True)

        original_code = 'var archive = new Archive();'
        trigger_info = {'keywords': ['zip', 'archive'], 'avoid_classes': [], 'reason': 'test'}

        result = service.find_substitute_example(
            original_code=original_code,
            trigger_info=trigger_info,
            family='zip',
            original_app_context='console'
        )

        assert result is not None
        _, example_id, _ = result
        assert example_id == 'small_console', "Should prefer smaller example when both match context"

    def test_config_flag_default_is_false(self):
        """Test that same_context_only defaults to False for backward compatibility"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            backfill_dir = Path(tmp_dir) / "backfill"
            backfill_dir.mkdir()

            # Initialize without explicit flag
            service = ExampleSubstitutionService(backfill_dir)

            assert service.same_context_only is False, "Default should be False for backward compatibility"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
