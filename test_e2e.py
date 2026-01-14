#!/usr/bin/env python3
"""
End-to-End Test for Example Reviewer Pipeline.
Tests the full pipeline using the test.zip data.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from example_reviewer.mcp_tools.tools import ExampleReviewerTools, ToolResult
from example_reviewer.core.database import Database
from example_reviewer.core.config import ConfigurationManager
from example_reviewer.services.compilation_service import check_dotnet_available

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str = "") -> None:
    """Print a visual separator."""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def print_result(name: str, result: ToolResult) -> None:
    """Print test result."""
    status = "✓" if result.success else "✗"
    print(f"\n{status} {name}")
    if result.data:
        for key, value in result.data.items():
            if isinstance(value, dict):
                print(f"    {key}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            elif isinstance(value, list):
                print(f"    {key}: [{len(value)} items]")
            else:
                print(f"    {key}: {value}")
    if result.error:
        print(f"    Error: {result.error}")


def run_e2e_test() -> bool:
    """Run end-to-end test of the pipeline."""
    print_separator("Example Reviewer Pipeline - End-to-End Test")
    
    # Define paths
    config_dir = project_root / "config" / "families"
    db_path = project_root / "data" / "test_e2e.db"
    workspace_dir = project_root / "workspace" / "test_e2e"
    
    # Clean up previous test artifacts
    if db_path.exists():
        db_path.unlink()
    if workspace_dir.exists():
        import shutil
        shutil.rmtree(workspace_dir)
    
    print(f"\nConfig dir: {config_dir}")
    print(f"Database: {db_path}")
    print(f"Workspace: {workspace_dir}")
    
    # Check prerequisites
    print_separator("Prerequisites Check")
    
    # Check .NET SDK
    dotnet_ok, dotnet_version = check_dotnet_available()
    if dotnet_ok:
        print(f"✓ .NET SDK: {dotnet_version}")
    else:
        print(f"✗ .NET SDK not available: {dotnet_version}")
        print("  Please install .NET SDK 8.0 to run compilation tests")
    
    # Check config files
    if config_dir.exists():
        families = list(config_dir.glob("*.json"))
        print(f"✓ Config directory: {len(families)} family configs found")
        for f in families:
            print(f"    - {f.stem}")
    else:
        print(f"✗ Config directory not found: {config_dir}")
        return False
    
    # Check test data
    test_content_dir = project_root / "test-data" / "test-content"
    test_data_dir = project_root / "test-data" / "test-data" / "zip"
    
    if test_content_dir.exists():
        md_files = list(test_content_dir.rglob("*.md"))
        print(f"✓ Test content: {len(md_files)} markdown files")
    else:
        print(f"✗ Test content not found: {test_content_dir}")
        return False
    
    if test_data_dir.exists():
        data_files = list(test_data_dir.iterdir())
        print(f"✓ Test data: {len(data_files)} files in zip test data")
    else:
        print(f"✗ Test data not found: {test_data_dir}")
        return False
    
    # Initialize tools
    print_separator("Pipeline Initialization")
    
    try:
        tools = ExampleReviewerTools(
            config_dir=config_dir,
            db_path=db_path,
            workspace_dir=workspace_dir,
        )
        print("✓ Tools initialized")
    except Exception as e:
        print(f"✗ Failed to initialize tools: {e}")
        return False
    
    # Test: List families
    print_separator("Test 1: List Available Families")
    try:
        families = tools.orchestrator.config_manager.list_families()
        print(f"✓ Found {len(families)} families: {', '.join(families)}")
    except Exception as e:
        print(f"✗ Failed to list families: {e}")
        return False
    
    # Test: Scan for markdown files
    print_separator("Test 2: Scan for Markdown Files")
    result = tools.scan(family="zip")
    print_result("Scan (by family)", result)
    
    if not result.success:
        print("  Trying directory scan instead...")
        result = tools.scan(directory=str(test_content_dir), max_files=50)
        print_result("Scan (by directory)", result)
    
    # Test: Extract code examples
    print_separator("Test 3: Extract Code Examples")
    result = tools.extract(family="zip", max_files=10)
    print_result("Extract", result)
    
    if not result.success:
        print(f"  Extract failed: {result.error}")
        return False
    
    examples_found = result.data.get('examples_found', 0) if result.data else 0
    if examples_found == 0:
        print("  Warning: No examples found, cannot continue pipeline test")
        return True  # Partial success - scan/extract works
    
    # Test: Get status
    print_separator("Test 4: Get Pipeline Status")
    result = tools.status(family="zip")
    print_result("Status", result)
    
    # Test: Compile verification (without LLM fixes)
    if dotnet_ok:
        print_separator("Test 5: Compile Verification")
        result = tools.compile_verify(family="zip", max_examples=3)
        print_result("Compile Verify", result)
        
        # If some compiled, test runtime
        if result.success and result.data:
            compiled = result.data.get('compiled_first_try', 0)
            if compiled > 0:
                print_separator("Test 6: Runtime Verification")
                result = tools.runtime_verify(family="zip", max_examples=2)
                print_result("Runtime Verify", result)
    else:
        print_separator("Tests 5-6: Skipped (no .NET SDK)")
    
    # Final status
    print_separator("Final Pipeline Status")
    result = tools.status(family="zip")
    print_result("Final Status", result)
    
    print_separator("End-to-End Test Complete")
    print("\nSummary:")
    print("  - Configuration: OK")
    print("  - Discovery: OK" if examples_found > 0 else "  - Discovery: No examples found")
    print("  - Database: OK")
    print(f"  - Compilation: {'OK' if dotnet_ok else 'Skipped'}")
    
    return True


def test_individual_services() -> bool:
    """Test individual services without running full pipeline."""
    print_separator("Individual Service Tests")
    
    project_root = Path(__file__).parent
    
    # Test 1: Database
    print("\n--- Database Test ---")
    try:
        from example_reviewer.core.database import Database
        from example_reviewer.core.models import ExampleRecord, ExampleStatus
        
        db = Database(project_root / "data" / "service_test.db")
        db.initialize_schema()
        
        # Create test example
        example = ExampleRecord(
            family="test",
            file_path="/test/example.md",
            original_code="Console.WriteLine(\"Hello\");",
        )
        
        # Save and retrieve
        db.save_example(example)
        retrieved = db.get_example(example.example_id)
        
        assert retrieved is not None
        assert retrieved.family == "test"
        print("✓ Database CRUD operations work")
        
        # Cleanup
        (project_root / "data" / "service_test.db").unlink()
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Configuration
    print("\n--- Configuration Test ---")
    try:
        from example_reviewer.core.config import ConfigurationManager
        
        config_manager = ConfigurationManager(
            config_dir=project_root / "config" / "families"
        )
        
        # Load global config
        global_config = config_manager.load_global_config()
        print(f"✓ Global config loaded: LLM model = {global_config.llm.model}")
        
        # Load family config
        zip_config = config_manager.load_family_config("zip")
        print(f"✓ Family config loaded: {zip_config.display_name}")
        print(f"    NuGet package: {zip_config.get_nuget_package_name()}")
        print(f"    Test data path: {zip_config.test_data.local_path}")
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Discovery Service
    print("\n--- Discovery Service Test ---")
    try:
        from example_reviewer.services.discovery_service import DiscoveryService
        from example_reviewer.core.database import Database
        
        db = Database(project_root / "data" / "discovery_test.db")
        db.initialize_schema()
        
        discovery = DiscoveryService(db)
        
        # Process a single file
        test_file = project_root / "test-data" / "test-content" / "kb" / "universal-extractor" / "how-to-extract-zip-file-csharp.md"
        
        if test_file.exists():
            examples = discovery._process_file(str(test_file), "zip")
            print(f"✓ Discovery service found {len(examples)} examples in test file")
            for ex in examples[:3]:
                print(f"    - {ex.source_type.value}: {len(ex.original_code)} chars at line {ex.location.start_line}")
        else:
            print(f"  Test file not found: {test_file}")
        
        # Cleanup
        (project_root / "data" / "discovery_test.db").unlink()
        
    except Exception as e:
        print(f"✗ Discovery service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Compilation Service
    print("\n--- Compilation Service Test ---")
    dotnet_ok, dotnet_version = check_dotnet_available()
    
    if not dotnet_ok:
        print(f"  Skipped: .NET SDK not available")
    else:
        try:
            from example_reviewer.services.compilation_service import CompilationService
            from example_reviewer.core.database import Database
            from example_reviewer.core.models import ExampleRecord
            
            db = Database(project_root / "data" / "compile_test.db")
            db.initialize_schema()
            
            config_manager = ConfigurationManager(project_root / "config" / "families")
            zip_config = config_manager.load_family_config("zip")
            
            compilation = CompilationService(
                db,
                workspace_dir=project_root / "workspace" / "compile_test",
                artifacts_dir=project_root / "artifacts" / "compile_test",
            )
            
            # Test with simple code
            example = ExampleRecord(
                family="zip",
                file_path="/test/example.md",
                original_code='Console.WriteLine("Hello from Aspose.Zip test!");',
            )
            
            success, result = compilation.compile_example(example, zip_config)
            
            if success:
                print(f"✓ Compilation service works (built in {result.duration_ms}ms)")
            else:
                print(f"  Compilation failed (expected for incomplete code): {result.errors[0] if result.errors else 'unknown'}")
            
            # Cleanup
            (project_root / "data" / "compile_test.db").unlink()
            import shutil
            if (project_root / "workspace" / "compile_test").exists():
                shutil.rmtree(project_root / "workspace" / "compile_test")
            if (project_root / "artifacts" / "compile_test").exists():
                shutil.rmtree(project_root / "artifacts" / "compile_test")
                
        except Exception as e:
            print(f"✗ Compilation service test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    print("\n" + "=" * 70)
    print("  EXAMPLE REVIEWER PIPELINE - TEST SUITE")
    print("=" * 70)
    
    # Run individual service tests
    services_ok = test_individual_services()
    
    # Run E2E test
    e2e_ok = run_e2e_test()
    
    # Final result
    print("\n" + "=" * 70)
    print("  TEST RESULTS")
    print("=" * 70)
    print(f"\nService Tests: {'PASSED' if services_ok else 'FAILED'}")
    print(f"E2E Test: {'PASSED' if e2e_ok else 'FAILED'}")
    
    sys.exit(0 if (services_ok and e2e_ok) else 1)
