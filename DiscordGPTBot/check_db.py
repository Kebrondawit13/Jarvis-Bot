import sqlite3

conn = sqlite3.connect("javris_memory.db")
c = conn.cursor()

c.execute("PRAGMA table_info(memory)")

for row in c.fetchall():
    print(row)

conn.close()