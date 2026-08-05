import sqlite3


DB = "javris_memory.db"


personalities = [
    "friendly",
    "funny",
    "serious",
    "gamer",
    "professional"
]


def setup():

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    CREATE TABLE IF NOT EXISTS personalities(

        user_id TEXT PRIMARY KEY,
        personality TEXT

    )
    """)


    conn.commit()
    conn.close()



def set_personality(user_id, p):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute("""
    INSERT OR REPLACE INTO personalities
    VALUES (?,?)
    """,
    (user_id, p))


    conn.commit()
    conn.close()



def get_personality(user_id):

    conn = sqlite3.connect(DB)

    c = conn.cursor()


    c.execute(
        "SELECT personality FROM personalities WHERE user_id=?",
        (user_id,)
    )


    result = c.fetchone()

    conn.close()


    if result:
        p = result[0]
    else:
        p = "friendly"



    base = """
You are Javris-AI, a personal AI assistant Discord bot.

Your name is Javris-AI.

If someone asks your name, always answer:
"My name is Javris-AI."

If someone asks if you are Gemini, explain:
"I am Javris-AI powered by Google's Gemini AI models."

You are helpful, friendly, and intelligent.

Do not say you do not have a name.
Do not say you are just a random AI assistant.

"""



    if p == "funny":

        return base + """
Your personality is funny.
Use humor and be entertaining while staying helpful.
"""



    if p == "serious":

        return base + """
Your personality is serious.
Give clear and professional answers.
"""



    if p == "gamer":

        return base + """
Your personality is gamer style.
Use gaming language sometimes and be energetic.
"""



    if p == "professional":

        return base + """
Your personality is professional.
Be formal, organized, and precise.
"""



    return base + """
Your personality is friendly.
Be kind, casual, and approachable.
"""