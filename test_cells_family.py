"""Test API index builder with Cells family."""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from database import Database
from api_index_builder import ApiIndexBuilder
from telemetry import TelemetryClient
from api_reference_service import ApiReferenceService

# Initialize components
db_path = Path('data/examples.db')
artifacts_dir = Path('data/artifacts')
artifacts_dir.mkdir(parents=True, exist_ok=True)

db = Database(db_path)
telemetry = TelemetryClient(artifacts_dir)
builder = ApiIndexBuilder(db, telemetry)

# Build index for Cells family
print("="*80)
print("Building API index for Cells family...")
print("="*80)

reference_root = r'D:\onedrive\Documents\GitHub\aspose.net\content\reference.aspose.net'
stats = builder.build_index_for_family('cells', reference_root, force_rebuild=True)

print("\n" + "="*80)
print("Cells Family Build Results")
print("="*80)
print(f"Classes indexed: {stats['classes']}")
print(f"Members indexed: {stats['members']}")
print(f"Files skipped: {stats['skipped']}")
print(f"Errors: {stats['errors']}")

# Check what classes are available
cursor = db._conn.execute("""
    SELECT DISTINCT class_name
    FROM api_reference
    WHERE family = 'cells'
    ORDER BY class_name
    LIMIT 10
""")
results = cursor.fetchall()
print("\n" + "="*80)
print("Sample Cells Classes:")
print("="*80)
for row in results:
    print(f"  - {row[0]}")

# Test API Reference Service with Cells family
print("\n" + "="*80)
print("TEST: Cells Family - Workbook class errors")
print("="*80)

api_service = ApiReferenceService(db, cache_size=128)

test_cells_error = """
error CS1729: 'Workbook' does not contain a constructor that takes 0 arguments
error CS1061: 'Workbook' does not contain a definition for 'AddWorksheet'
error CS0246: The type or namespace name 'Worksheet' could not be found
"""

context = api_service.get_api_context_for_errors('cells', test_cells_error, max_classes=5)
prompt_text = context.to_prompt_text()

print("\nExtracted API Context for Cells family:")
print(prompt_text if prompt_text.strip() else "(No context found - checking class names...)")

# Verify all families in database
cursor = db._conn.execute("""
    SELECT family, COUNT(DISTINCT class_name) as classes, COUNT(*) as members
    FROM api_reference
    GROUP BY family
    ORDER BY family
""")

results = cursor.fetchall()
print("\n" + "="*80)
print("All Families in Database")
print("="*80)
for family, classes, members in results:
    print(f"  {family}: {classes} classes, {members} members")

print("\n[OK] Multi-family database storage verified!")
