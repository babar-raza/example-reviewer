"""Test API Reference Service with simulated compilation errors."""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from database import Database
from api_reference_service import ApiReferenceService

# Initialize database and service
db = Database(Path('data/examples.db'))
api_service = ApiReferenceService(db, cache_size=128)

# Test with actual errors from Run 24
print("="*80)
print("TEST 1: Snippet 138 errors (DeflateCompressionSettings constructor)")
print("="*80)

test_error_138 = """
error CS1729: 'DeflateCompressionSettings' does not contain a constructor that takes 1 arguments
error CS1061: 'Archive' does not contain a definition for 'AddEntry'
"""

context = api_service.get_api_context_for_errors('zip', test_error_138, max_classes=5)
prompt_text = context.to_prompt_text()

print("\nExtracted API Context:")
print(prompt_text)

print("\n" + "="*80)
print("TEST 2: Snippet 136 errors (Archive.Entries.Add)")
print("="*80)

test_error_136 = """
error CS0118: 'Archive.Entries' is a property but is used like a type
error CS1061: 'ReadOnlyCollection<ArchiveEntry>' does not contain a definition for 'Add'
"""

context2 = api_service.get_api_context_for_errors('zip', test_error_136, max_classes=5)
prompt_text2 = context2.to_prompt_text()

print("\nExtracted API Context:")
print(prompt_text2)

# Check cache stats
print("\n" + "="*80)
print("Cache Statistics:")
print("="*80)
stats = api_service.get_cache_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

print("\n" + "="*80)
print("Done!")
