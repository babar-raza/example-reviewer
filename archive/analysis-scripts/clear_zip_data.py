import sqlite3

conn = sqlite3.connect(r'c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\data\examples.db')
cursor = conn.cursor()

# Delete all ZIP family data
cursor.execute("""
    DELETE FROM snippets
    WHERE page_id IN (SELECT page_id FROM pages WHERE family = 'zip')
""")
snippets_deleted = cursor.rowcount

cursor.execute("DELETE FROM pages WHERE family = 'zip'")
pages_deleted = cursor.rowcount

conn.commit()
conn.close()

print(f"Deleted {pages_deleted} pages and {snippets_deleted} snippets for ZIP family")
