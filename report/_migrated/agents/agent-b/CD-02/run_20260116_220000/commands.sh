#!/bin/bash
# CD-02: Add Line Count and Content-Based Filtering
# Agent B - Implementation
# All commands executed during implementation

# ============================================================
# PHASE 1: Configuration Model Implementation
# ============================================================

# Added DiscoveryPatternsConfig class to src/core/config.py
# Added filtering fields: min_line_count, max_line_count, content_exclude_patterns, require_code_indicators
# Updated GlobalConfig to include discovery_patterns field
# Updated _parse_global_config to parse discovery_patterns section

# ============================================================
# PHASE 2: Filtering Logic Implementation
# ============================================================

# Updated src/services/discovery_service.py:
# - Added import for DiscoveryPatternsConfig
# - Added filtering_config parameter to __init__
# - Added filter_snippet method
# - Added _track_filter_reason method
# - Added get_filter_stats method
# - Integrated filtering into _extract_inline_examples
# - Added filter statistics to discover_family return value

# Updated src/pipeline/orchestrator.py:
# - Pass global discovery_patterns config to DiscoveryService

# ============================================================
# PHASE 3: Configuration Files Update
# ============================================================

# Updated config/global.json with discovery_patterns section
# (CD-01 fields were already present, added CD-02 filtering fields)

# ============================================================
# PHASE 4: Unit Testing
# ============================================================

# Create test file
# tests/test_discovery_filters.py created with 13 tests

# Install test dependencies
pip install --user pytest pytest-asyncio pytest-mock

# Run tests (all tests passing)
cd "c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer"
.venv/Scripts/python.exe -m pytest tests/test_discovery_filters.py -v

# Save test output
.venv/Scripts/python.exe -m pytest tests/test_discovery_filters.py -v > reports/agents/agent-b/CD-02/run_20260116_220000/artifacts/test_output.txt 2>&1

# ============================================================
# PHASE 5: Verification Commands
# ============================================================

# Test configuration loading
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, '.')
from src.core.config import DiscoveryPatternsConfig
config = DiscoveryPatternsConfig()
print(f'min_line_count: {config.min_line_count}')
print(f'max_line_count: {config.max_line_count}')
print(f'content_exclude_patterns: {len(config.content_exclude_patterns)} patterns')
print(f'require_code_indicators: {len(config.require_code_indicators)} patterns')
"

# Test filter_snippet functionality
.venv/Scripts/python.exe debug_filter.py

# Run discovery on ZIP family (integration test)
# python -m src.cli.main discover --family zip
# (Would require content directory setup)

# ============================================================
# FILE CHANGES SUMMARY
# ============================================================
# Modified:
#   - src/core/config.py (added CD-02 filtering fields to DiscoveryPatternsConfig)
#   - src/services/discovery_service.py (added filtering logic)
#   - src/pipeline/orchestrator.py (pass filtering config)
#   - config/global.json (added CD-02 configuration fields)
# Created:
#   - tests/test_discovery_filters.py (13 unit tests)
#   - debug_filter.py (debugging script)
#   - reports/agents/agent-b/CD-02/run_20260116_220000/plan.md
#   - reports/agents/agent-b/CD-02/run_20260116_220000/commands.sh
#   - reports/agents/agent-b/CD-02/run_20260116_220000/artifacts/test_output.txt

# ============================================================
# TEST RESULTS
# ============================================================
# All 13 tests PASSED in 1.47s:
#   - TestLineCountFiltering: 3/3 tests passed
#   - TestContentExclusionPatterns: 4/4 tests passed
#   - TestCodeIndicators: 3/3 tests passed
#   - TestFilterStatistics: 1/1 test passed
#   - TestFilterIntegration: 2/2 tests passed

# ============================================================
# VERIFICATION STATUS
# ============================================================
# ✓ Line count filtering working (min=5, max=500 defaults)
# ✓ Content exclusion patterns working (JSON, XML, output excluded)
# ✓ Code indicator check working (requires C# keywords)
# ✓ Filter statistics tracked
# ✓ Filter reasons logged and counted
# ✓ Unit tests passing (13/13 tests)
# ✓ No false negatives (real code snippets included)
