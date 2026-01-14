import sqlite3

conn = sqlite3.connect('data/examples.db')

# Check member type distribution
cursor = conn.execute('''
    SELECT member_type, COUNT(*) as count
    FROM api_reference
    WHERE family="zip"
    GROUP BY member_type
    ORDER BY count DESC
''')
print('Member type distribution:')
for row in cursor:
    print(f'  {row[0]}: {row[1]}')

# Check total distinct classes
cursor = conn.execute('SELECT COUNT(DISTINCT class_name) FROM api_reference WHERE family="zip"')
print(f'\nTotal distinct classes: {cursor.fetchone()[0]}')

# Show a sample of classes
cursor = conn.execute('''
    SELECT DISTINCT class_name
    FROM api_reference
    WHERE family="zip"
    LIMIT 10
''')
print('\nSample classes:')
for row in cursor:
    print(f'  - {row[0]}')

# Show a sample entry with details
cursor = conn.execute('''
    SELECT class_name, member_type, member_name, signature
    FROM api_reference
    WHERE family="zip"
    LIMIT 5
''')
print('\nSample entries:')
for row in cursor:
    print(f'  {row[0]} ({row[1]}): {row[2] or "N/A"}')
    print(f'    Signature: {row[3][:80]}...' if len(row[3]) > 80 else f'    Signature: {row[3]}')

conn.close()
