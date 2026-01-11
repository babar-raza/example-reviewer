import sqlite3

conn = sqlite3.connect(r'c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\data\examples.db')
cursor = conn.cursor()

# Get the code content for snippet 2
cursor.execute('''
    SELECT sv.code_content
    FROM snippet_versions sv
    WHERE sv.snippet_id = 2
    ORDER BY sv.created_at DESC
    LIMIT 1
''')

row = cursor.fetchone()
if row:
    print("=== Snippet 2 Code ===")
    print(row[0])
else:
    print("No code found for snippet 2")

conn.close()
