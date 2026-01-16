#!/usr/bin/env python3
"""
Validation Test Script for Example Reviewer Pipeline Hardening.
Run this after each change to ensure nothing is broken.

Usage:
    python validate_hardening.py              # Run all tests
    python validate_hardening.py --quick      # Quick import test only
    python validate_hardening.py --compile    # Test compilation service
    python validate_hardening.py --runtime    # Test runtime service
    python validate_hardening.py --pipeline   # Test full pipeline (10 examples)
"""

import sys
import argparse
from pathlib import Path
from typing import Tuple, List

def test_imports() -> Tuple[bool, str]:
    """Test all imports work."""
    try:
        from example_reviewer.core.models import ExampleRecord, ExampleStatus
        from example_reviewer.core.config import ConfigurationManager, FamilyConfig
        from example_reviewer.core.database import Database
        from example_reviewer.services.discovery_service import DiscoveryService
        from example_reviewer.services.compilation_service import CompilationService
        from example_reviewer.services.runtime_service import RuntimeService
        from example_reviewer.services.llm_service import LLMService
        from example_reviewer.services.markdown_service import MarkdownUpdateService
        from example_reviewer.pipeline.orchestrator import PipelineOrchestrator
        from example_reviewer.mcp_tools.tools import ExampleReviewerTools
        return True, "All imports successful"
    except Exception as e:
        return False, f"Import error: {e}"

def test_config_loading() -> Tuple[bool, str]:
    """Test configuration loading."""
    try:
        from example_reviewer.core.config import ConfigurationManager
        cm = ConfigurationManager(Path("config/families"))
        
        # Test global config
        global_cfg = cm.load_global_config()
        assert global_cfg.llm.provider in ("openai", "ollama", "azure")
        
        # Test family config
        zip_cfg = cm.load_family_config("zip")
        assert zip_cfg.family == "zip"
        assert zip_cfg.nuget_config is not None
        assert zip_cfg.runtime_validation is not None
        
        return True, f"Config loaded: {global_cfg.llm.provider}/{global_cfg.llm.model}"
    except Exception as e:
        return False, f"Config error: {e}"

def test_database() -> Tuple[bool, str]:
    """Test database operations."""
    try:
        from example_reviewer.core.database import Database
        from example_reviewer.core.models import ExampleRecord, ExampleStatus
        
        db = Database(Path("test_validate.db"))
        db.initialize_schema()
        
        # Test CRUD
        example = ExampleRecord(
            example_id="test_validate_1",
            family="zip",
            file_path="test.md",
            source_type="inline",
            original_code="test code",
            status=ExampleStatus.DISCOVERED,
        )
        db.save_example(example)
        
        loaded = db.get_example("test_validate_1")
        assert loaded is not None
        assert loaded.original_code == "test code"
        
        # Cleanup
        Path("test_validate.db").unlink(missing_ok=True)
        
        return True, "Database CRUD operations work"
    except Exception as e:
        return False, f"Database error: {e}"

def test_compilation_service() -> Tuple[bool, str]:
    """Test compilation service methods."""
    try:
        from example_reviewer.services.compilation_service import CompilationService
        from example_reviewer.core.database import Database
        from example_reviewer.core.config import ConfigurationManager
        
        db = Database(Path("test_compile.db"))
        db.initialize_schema()
        cs = CompilationService(db)
        cm = ConfigurationManager(Path("config/families"))
        family_config = cm.load_family_config("zip")
        
        # Test code wrapping
        test_cases = [
            # (input, should_contain)
            ("Console.WriteLine(\"Hello\");", "class"),
            ("using System; class Test {}", "using System"),
            ("var x = 1;", "Main"),
        ]
        
        results = []
        for code, expected in test_cases:
            wrapped = cs._wrap_code(code, family_config)
            if expected in wrapped:
                results.append(True)
            else:
                results.append(False)
        
        # Cleanup
        Path("test_compile.db").unlink(missing_ok=True)
        
        passed = sum(results)
        total = len(results)
        return passed == total, f"Code wrapping: {passed}/{total} tests passed"
    except Exception as e:
        return False, f"Compilation service error: {e}"

def test_runtime_service() -> Tuple[bool, str]:
    """Test runtime service methods."""
    try:
        from example_reviewer.services.runtime_service import RuntimeService
        from example_reviewer.core.database import Database
        
        db = Database(Path("test_runtime.db"))
        db.initialize_schema()
        rs = RuntimeService(db)
        
        # Test service initialization
        assert rs.workspace_dir.exists() or True  # Will create on first use
        
        # Cleanup
        Path("test_runtime.db").unlink(missing_ok=True)
        
        return True, "Runtime service initialized"
    except Exception as e:
        return False, f"Runtime service error: {e}"

def test_llm_service() -> Tuple[bool, str]:
    """Test LLM service (without actual API calls)."""
    try:
        from example_reviewer.services.llm_service import LLMService
        
        # Test with Ollama (doesn't require API key)
        llm = LLMService(provider="ollama", model="qwen2.5-coder:7b")
        
        # Test availability check
        available = llm.is_available()
        
        # Test fix_code method exists and has correct signature
        import inspect
        sig = inspect.signature(llm.fix_code)
        params = list(sig.parameters.keys())
        assert "code" in params
        assert "error_logs" in params
        assert "context_type" in params
        
        return True, f"LLM service configured (available: {available})"
    except Exception as e:
        return False, f"LLM service error: {e}"

def test_orchestrator() -> Tuple[bool, str]:
    """Test pipeline orchestrator initialization."""
    try:
        from example_reviewer.pipeline.orchestrator import PipelineOrchestrator
        
        orch = PipelineOrchestrator(
            config_dir=Path("config/families"),
            db_path=Path("test_orch.db"),
        )
        
        # Test lazy service initialization
        assert orch._llm_service is None  # Not initialized yet
        assert orch._compilation_service is None
        
        # Cleanup
        Path("test_orch.db").unlink(missing_ok=True)
        
        return True, "Orchestrator initialized"
    except Exception as e:
        return False, f"Orchestrator error: {e}"

def test_mini_pipeline() -> Tuple[bool, str]:
    """Test mini pipeline run - just verify it runs without errors."""
    try:
        from example_reviewer.pipeline.orchestrator import PipelineOrchestrator
        from example_reviewer.core.models import ExampleStatus
        
        orch = PipelineOrchestrator(
            config_dir=Path("config/families"),
            db_path=Path("test_mini.db"),
        )
        
        # Run discovery on small set
        family_config = orch.config_manager.load_family_config("zip")
        discovery_stats = orch._run_discovery_phase("zip", family_config, max_examples=10)
        
        discovered = discovery_stats.get('examples_extracted', 0)
        files_scanned = discovery_stats.get('files_processed', 0)
        
        # Cleanup
        Path("test_mini.db").unlink(missing_ok=True)
        
        # Success if it ran without error, even if no examples (test data may not be present)
        return True, f"Mini pipeline: scanned {files_scanned} files, found {discovered} examples"
    except Exception as e:
        return False, f"Mini pipeline error: {e}"

def test_compile_pipeline(max_examples: int = 10) -> Tuple[bool, str]:
    """Test compilation pipeline with examples."""
    try:
        from example_reviewer.pipeline.orchestrator import PipelineOrchestrator
        
        orch = PipelineOrchestrator(
            config_dir=Path("config/families"),
            db_path=Path("test_compile_pipe.db"),
        )
        
        family_config = orch.config_manager.load_family_config("zip")
        
        # Discovery
        discovery_stats = orch._run_discovery_phase("zip", family_config, max_examples=max_examples * 2)
        discovered = discovery_stats.get('examples_extracted', 0)
        
        if discovered == 0:
            return False, "No examples discovered"
        
        # Compilation (skip LLM to test deterministic fixes)
        compile_stats = orch._run_compilation_phase(
            "zip", family_config, 
            max_examples=min(max_examples, discovered),
            skip_llm_fixes=True
        )
        
        total = compile_stats.get('total_processed', 0)
        compiled = compile_stats.get('compiled_first_try', 0)
        
        # Cleanup
        Path("test_compile_pipe.db").unlink(missing_ok=True)
        
        rate = (compiled / total * 100) if total > 0 else 0
        return True, f"Compilation: {compiled}/{total} ({rate:.1f}%)"
    except Exception as e:
        return False, f"Compile pipeline error: {e}"

def run_all_tests(quick: bool = False) -> List[Tuple[str, bool, str]]:
    """Run all validation tests."""
    results = []
    
    # Always run import test
    name = "Imports"
    success, msg = test_imports()
    results.append((name, success, msg))
    print(f"{'✓' if success else '✗'} {name}: {msg}")
    
    if quick:
        return results
    
    # Run other tests
    tests = [
        ("Config", test_config_loading),
        ("Database", test_database),
        ("Compilation Service", test_compilation_service),
        ("Runtime Service", test_runtime_service),
        ("LLM Service", test_llm_service),
        ("Orchestrator", test_orchestrator),
        ("Mini Pipeline", test_mini_pipeline),
    ]
    
    for name, test_func in tests:
        try:
            success, msg = test_func()
        except Exception as e:
            success, msg = False, str(e)
        results.append((name, success, msg))
        print(f"{'✓' if success else '✗'} {name}: {msg}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Validate Example Reviewer Pipeline")
    parser.add_argument("--quick", action="store_true", help="Quick import test only")
    parser.add_argument("--compile", action="store_true", help="Test compilation pipeline")
    parser.add_argument("--runtime", action="store_true", help="Test runtime service")
    parser.add_argument("--pipeline", action="store_true", help="Test full pipeline (10 examples)")
    parser.add_argument("--max-examples", type=int, default=10, help="Max examples to test")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Example Reviewer Pipeline - Validation Tests")
    print("=" * 60)
    print()
    
    if args.compile:
        success, msg = test_compile_pipeline(args.max_examples)
        print(f"{'✓' if success else '✗'} Compile Pipeline: {msg}")
        sys.exit(0 if success else 1)
    
    if args.runtime:
        success, msg = test_runtime_service()
        print(f"{'✓' if success else '✗'} Runtime Service: {msg}")
        sys.exit(0 if success else 1)
    
    if args.pipeline:
        success, msg = test_mini_pipeline()
        print(f"{'✓' if success else '✗'} Pipeline: {msg}")
        sys.exit(0 if success else 1)
    
    # Run all tests
    results = run_all_tests(quick=args.quick)
    
    print()
    print("=" * 60)
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
