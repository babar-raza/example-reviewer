#!/usr/bin/env python
"""Debug script for testing filter_snippet."""

import sys
sys.path.insert(0, '.')

from src.core.database import Database
from src.core.config import DiscoveryPatternsConfig
from src.services.discovery_service import DiscoveryService

# Create test database
db = Database(":memory:")
db.initialize_schema()

# Create config and service
config = DiscoveryPatternsConfig()
service = DiscoveryService(db, filtering_config=config)

# Test code
code = """using System;
using Aspose.Zip;

public class Example
{
    public void Method()
    {
        var archive = new Archive();
    }
}"""

print("Testing filter_snippet...")
print(f"Config min_line_count: {config.min_line_count}")
print(f"Config max_line_count: {config.max_line_count}")
print(f"Config content_exclude_patterns: {config.content_exclude_patterns}")
print(f"Config require_code_indicators: {config.require_code_indicators}")
print()

lines = code.strip().split('\n')
print(f"Code has {len(lines)} lines")
print()

should_include, reason = service.filter_snippet(code)
print(f"Result: should_include={should_include}, reason={reason}")
