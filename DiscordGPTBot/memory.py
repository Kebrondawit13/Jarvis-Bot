import sqlite3
from datetime import datetime


DB = "javris_memory.db"



def setup():

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    CREATE TABLE IF NOT EXISTS memory(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id TEXT,

        role TEXT,

        content TEXT,

        username TEXT,

        time TEXT

    )
    """)


    conn.commit()

    conn.close()





def save_message(user_id, role, content, username):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    INSERT INTO memory
    (
        user_id,
        role,
        content,
        username,
        time
    )

    VALUES (?,?,?,?,?)

    """,
    (
        user_id,
        role,
        content,
        username,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))


    conn.commit()

    conn.close()





def get_memory(user_id):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    SELECT role, content

    FROM memory

    WHERE user_id=?

    ORDER BY id DESC

    LIMIT 10

    """,
    (user_id,))


    data = c.fetchall()


    conn.close()


    data.reverse()


    return [

        {
            "role": row[0],
            "content": row[1]
        }

        for row in data

    ]






def forget(user_id):

    clear_user(user_id)






def clear_user(user_id):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute(
        "DELETE FROM memory WHERE user_id=?",
        (user_id,)
    )


    conn.commit()

    conn.close()






def get_users():

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    SELECT

        user_id,

        MAX(username),

        COUNT(*),

        MAX(time)

    FROM memory

    GROUP BY user_id

    ORDER BY MAX(time) DESC

    """)


    data = c.fetchall()


    conn.close()


    return data






def get_history(user_id):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    SELECT

        role,

        content,

        time

    FROM memory

    WHERE user_id=?

    ORDER BY id ASC

    """,
    (user_id,))


    data = c.fetchall()


    conn.close()


    return data






def get_latest_messages():

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    SELECT

        username,

        role,

        content,

        time

    FROM memory

    ORDER BY id DESC

    LIMIT 50

    """)


    data = c.fetchall()


    conn.close()


    return data






def search_messages(text):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    SELECT

        user_id,

        username

    FROM memory

    WHERE content LIKE ?

    GROUP BY user_id

    """,
    (
        "%" + text + "%",
    ))


    data = c.fetchall()


    conn.close()


    return data






def get_message_count():

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute(
        "SELECT COUNT(*) FROM memory"
    )


    count = c.fetchone()[0]


    conn.close()


    return count