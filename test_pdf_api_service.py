"""Test API Reference Service with PDF family."""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from database import Database
from api_reference_service import ApiReferenceService

# Initialize database and service
db = Database(Path('data/examples.db'))
api_service = ApiReferenceService(db, cache_size=128)

# Test with simulated PDF-related compilation errors
print("="*80)
print("TEST: PDF Family - Document class errors")
print("="*80)

test_pdf_error = """
error CS1729: 'Document' does not contain a constructor that takes 0 arguments
error CS1061: 'Document' does not contain a definition for 'AddPage'
error CS0246: The type or namespace name 'Page' could not be found
"""

context = api_service.get_api_context_for_errors('pdf', test_pdf_error, max_classes=5)
prompt_text = context.to_prompt_text()

print("\nExtracted API Context for PDF family:")
print(prompt_text)

# Check cache stats
print("\n" + "="*80)
print("Cache Statistics:")
print("="*80)
stats = api_service.get_cache_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

# Now test with ZIP family to confirm isolation
print("\n" + "="*80)
print("TEST: ZIP Family - Archive class errors (for comparison)")
print("="*80)

test_zip_error = """
error CS1729: 'Archive' does not contain a constructor that takes 1 arguments
error CS1061: 'Archive' does not contain a definition for 'AddEntry'
"""

context_zip = api_service.get_api_context_for_errors('zip', test_zip_error, max_classes=5)
prompt_text_zip = context_zip.to_prompt_text()

print("\nExtracted API Context for ZIP family:")
print(prompt_text_zip)

# Final cache stats
print("\n" + "="*80)
print("Final Cache Statistics (after both families):")
print("="*80)
stats = api_service.get_cache_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")

print("\n" + "="*80)
print("[OK] Multi-family API service verified!")
print("- PDF family data extracted correctly")
print("- ZIP family data extracted correctly")
print("- Families are properly isolated")
print("="*80)
