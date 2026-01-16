import sqlite3

conn = sqlite3.connect(r'c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\data\examples.db')
cursor = conn.cursor()

# Reset all ZIP family snippets from needs-fix to unverified
cursor.execute("""
    UPDATE snippets
    SET status = 'unverified'
    WHERE snippet_id IN (
        SELECT s.snippet_id
        FROM snippets s
        JOIN pages p ON s.page_id = p.page_id
        WHERE p.family = 'zip' AND s.status = 'needs-fix'
    )
""")

affected = cursor.rowcount
conn.commit()
conn.close()

print(f"Reset {affected} snippets from needs-fix to unverified")
