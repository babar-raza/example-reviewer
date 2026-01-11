import sqlite3

conn = sqlite3.connect(r'c:\Users\prora\OneDrive\Documents\GitHub\example-reviewer\data\examples.db')
cursor = conn.cursor()

# Count gist publications for ZIP family
cursor.execute("""
    SELECT COUNT(*)
    FROM gist_publications gp
    JOIN snippets s ON gp.snippet_id = s.snippet_id
    JOIN pages p ON s.page_id = p.page_id
    WHERE p.family = 'zip'
""")
total = cursor.fetchone()[0]
print(f"Total gist publications for ZIP: {total}")

if total > 0:
    cursor.execute("""
        SELECT gp.snippet_id, gp.new_gist_url, gp.new_gist_id, gp.status
        FROM gist_publications gp
        JOIN snippets s ON gp.snippet_id = s.snippet_id
        JOIN pages p ON s.page_id = p.page_id
        WHERE p.family = 'zip'
        ORDER BY gp.published_at DESC
        LIMIT 10
    """)
    print("\nRecent gist publications:")
    for row in cursor.fetchall():
        print(f"  Snippet {row[0]}: {row[1]} (ID: {row[2]}, Status: {row[3]})")

conn.close()
