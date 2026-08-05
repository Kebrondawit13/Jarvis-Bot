import sqlite3

DB = "javris_memory.db"

conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute("""
DELETE FROM memory
WHERE username IS NULL
""")

conn.commit()

print("Removed old broken memory entries")

conn.close()