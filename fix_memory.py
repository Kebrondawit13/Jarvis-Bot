import sqlite3

DB = "javris_memory.db"


conn = sqlite3.connect(DB)
c = conn.cursor()


try:

    c.execute("""
    ALTER TABLE memory
    ADD COLUMN id INTEGER
    """)

    print("Added id column")

except Exception as e:

    print(e)



conn.commit()
conn.close()


print("Database fixed")