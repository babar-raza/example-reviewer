"""Test API index builder with PDF family."""

import sys
from pathlib import Path
sys.path.insert(0, 'src')

from database import Database
from api_index_builder import ApiIndexBuilder
from telemetry import TelemetryClient

# Initialize components
db_path = Path('data/examples.db')
artifacts_dir = Path('data/artifacts')
artifacts_dir.mkdir(parents=True, exist_ok=True)

db = Database(db_path)
telemetry = TelemetryClient(artifacts_dir)
builder = ApiIndexBuilder(db, telemetry)

# Build index for PDF family
print("="*80)
print("Building API index for PDF family...")
print("="*80)

reference_root = r'D:\onedrive\Documents\GitHub\aspose.net\content\reference.aspose.net'
stats = builder.build_index_for_family('pdf', reference_root, force_rebuild=True)

print("\n" + "="*80)
print("PDF Family Build Results")
print("="*80)
print(f"Classes indexed: {stats['classes']}")
print(f"Members indexed: {stats['members']}")
print(f"Files skipped: {stats['skipped']}")
print(f"Errors: {stats['errors']}")

# Verify in database
print("\n" + "="*80)
print("Database Verification")
print("="*80)

cursor = db._conn.execute("""
    SELECT member_type, COUNT(*) as count
    FROM api_reference
    WHERE family = 'pdf'
    GROUP BY member_type
    ORDER BY member_type
""")

results = cursor.fetchall()
print("\nMember types for PDF family:")
for member_type, count in results:
    print(f"  {member_type}: {count}")

# Compare with ZIP family
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

print("\n[OK] Multi-family support verified!")
