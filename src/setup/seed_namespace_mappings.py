"""
Seed initial namespace-to-package mappings for automatic dependency resolution.

This script populates the namespace_to_package table with common mappings
for external packages used across Aspose code examples.
"""

import sqlite3
import sys
from pathlib import Path

# Initial seed mappings (namespace, package_name, version, source, confidence, notes)
INITIAL_MAPPINGS = [
    # System.Net.Http - common in PDF examples for API calls
    ('System.Net.Http', 'System.Net.Http', '4.3.4', 'manual', 1.0,
     'Required for HttpClient and HTTP API operations'),
    ('System.Net.Http.Headers', 'System.Net.Http', '4.3.4', 'manual', 1.0,
     'Part of System.Net.Http package'),
    ('System.Net.Http.Json', 'System.Net.Http.Json', '8.0.0', 'manual', 1.0,
     'JSON extension methods for HttpClient'),

    # Newtonsoft.Json - common for JSON serialization
    ('Newtonsoft.Json', 'Newtonsoft.Json', '13.0.3', 'manual', 1.0,
     'Industry standard JSON library'),
    ('Newtonsoft.Json.Linq', 'Newtonsoft.Json', '13.0.3', 'manual', 1.0,
     'LINQ to JSON functionality'),
    ('Newtonsoft.Json.Serialization', 'Newtonsoft.Json', '13.0.3', 'manual', 1.0,
     'Serialization customization'),

    # System.Data - database operations
    ('System.Data.SqlClient', 'System.Data.SqlClient', '4.8.6', 'manual', 1.0,
     'SQL Server database connectivity'),
    ('System.Data.Common', 'System.Data.Common', '8.0.0', 'manual', 0.9,
     'Common database abstractions'),

    # Azure - cloud storage
    ('Azure.Storage.Blobs', 'Azure.Storage.Blobs', '12.19.1', 'manual', 1.0,
     'Azure Blob Storage operations'),
    ('Azure.Storage.Files.Shares', 'Azure.Storage.Files.Shares', '12.16.0', 'manual', 0.9,
     'Azure File Shares'),
    ('Azure.Storage.Queues', 'Azure.Storage.Queues', '12.17.0', 'manual', 0.9,
     'Azure Queue Storage'),

    # Microsoft.Extensions - common for modern .NET apps
    ('Microsoft.Extensions.Configuration', 'Microsoft.Extensions.Configuration', '8.0.0', 'manual', 0.9,
     'Configuration system'),
    ('Microsoft.Extensions.DependencyInjection', 'Microsoft.Extensions.DependencyInjection', '8.0.0', 'manual', 0.9,
     'Dependency injection container'),
    ('Microsoft.Extensions.Logging', 'Microsoft.Extensions.Logging', '8.0.0', 'manual', 0.9,
     'Logging abstractions'),

    # ASP.NET Core - web applications (conditional)
    ('Microsoft.AspNetCore.Builder', 'Microsoft.AspNetCore.App', None, 'manual', 0.8,
     'ASP.NET Core framework reference (no explicit version)'),
    ('Microsoft.AspNetCore.Http', 'Microsoft.AspNetCore.App', None, 'manual', 0.8,
     'ASP.NET Core HTTP abstractions'),
    ('Microsoft.AspNetCore.Mvc', 'Microsoft.AspNetCore.App', None, 'manual', 0.8,
     'ASP.NET Core MVC framework'),

    # Entity Framework Core - database ORM
    ('Microsoft.EntityFrameworkCore', 'Microsoft.EntityFrameworkCore', '8.0.0', 'manual', 0.9,
     'EF Core ORM framework'),
    ('Microsoft.EntityFrameworkCore.SqlServer', 'Microsoft.EntityFrameworkCore.SqlServer', '8.0.0', 'manual', 0.9,
     'EF Core SQL Server provider'),
]

# BCL namespaces that don't require external packages
BCL_NAMESPACES = [
    ('System', None, None, 'bcl', 1.0, 'Base Class Library'),
    ('System.Collections', None, None, 'bcl', 1.0, 'Collection types'),
    ('System.Collections.Generic', None, None, 'bcl', 1.0, 'Generic collections'),
    ('System.Collections.Concurrent', None, None, 'bcl', 1.0, 'Concurrent collections'),
    ('System.IO', None, None, 'bcl', 1.0, 'File I/O'),
    ('System.IO.Compression', None, None, 'bcl', 1.0, 'Compression (built-in)'),
    ('System.Linq', None, None, 'bcl', 1.0, 'LINQ'),
    ('System.Text', None, None, 'bcl', 1.0, 'Text processing'),
    ('System.Text.RegularExpressions', None, None, 'bcl', 1.0, 'Regex'),
    ('System.Threading', None, None, 'bcl', 1.0, 'Threading'),
    ('System.Threading.Tasks', None, None, 'bcl', 1.0, 'Async/await'),
    ('System.Reflection', None, None, 'bcl', 1.0, 'Reflection'),
    ('System.Runtime', None, None, 'bcl', 1.0, 'Runtime services'),
    ('System.Diagnostics', None, None, 'bcl', 1.0, 'Diagnostics'),
    ('System.Globalization', None, None, 'bcl', 1.0, 'Globalization'),
    ('System.Security', None, None, 'bcl', 1.0, 'Security'),
    ('System.Security.Cryptography', None, None, 'bcl', 1.0, 'Cryptography'),
    ('System.Xml', None, None, 'bcl', 1.0, 'XML processing'),
    ('System.Xml.Linq', None, None, 'bcl', 1.0, 'LINQ to XML'),
]


def seed_mappings(db_path: str = 'data/examples.db'):
    """Seed namespace-to-package mappings into database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Seed BCL namespaces
    print(f"Seeding {len(BCL_NAMESPACES)} BCL namespace mappings...")
    for namespace, package, version, source, confidence, notes in BCL_NAMESPACES:
        cursor.execute("""
            INSERT OR IGNORE INTO namespace_to_package
            (namespace, package_name, package_version, source, confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (namespace, package or '', version, source, confidence, notes))

    # Seed external package mappings
    print(f"Seeding {len(INITIAL_MAPPINGS)} external package mappings...")
    for namespace, package, version, source, confidence, notes in INITIAL_MAPPINGS:
        cursor.execute("""
            INSERT OR IGNORE INTO namespace_to_package
            (namespace, package_name, package_version, source, confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (namespace, package, version, source, confidence, notes))

    conn.commit()

    # Verify seeding
    cursor.execute("SELECT source, COUNT(*) FROM namespace_to_package GROUP BY source")
    results = cursor.fetchall()

    print("\nSeeding complete!")
    print("Namespace-to-package mapping statistics:")
    for source, count in results:
        print(f"  {source}: {count} mappings")

    total = sum(count for _, count in results)
    print(f"  Total: {total} mappings")

    conn.close()


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'data/examples.db'

    # Verify database exists
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    seed_mappings(db_path)
