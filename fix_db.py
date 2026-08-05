import sqlite3

DB = "javris_memory.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


try:
    c.execute(
        "ALTER TABLE memory ADD COLUMN username TEXT"
    )
    print("Added username")

except:
    print("username already exists")



try:
    c.execute(
        "ALTER TABLE memory ADD COLUMN time TEXT"
    )
    print("Added time")

except:
    print("time already exists")



conn.commit()
conn.close()

print("Database fixed")