import sqlite3

DB = "javris_memory.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


try:

    c.execute("""
    ALTER TABLE memory
    ADD COLUMN username TEXT
    """)

    print("Added username column")

except Exception as e:

    print("Already exists:", e)



try:

    c.execute("""
    ALTER TABLE memory
    ADD COLUMN time TEXT
    """)

    print("Added time column")

except Exception as e:

    print("Already exists:", e)



conn.commit()
conn.close()


print("Database fixed")