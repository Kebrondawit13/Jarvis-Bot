# bot_status.py

online = False
username = "Offline"
servers = 0
users = 0

members = []



def setup():

    global online
    global username
    global servers
    global users
    global members

    online = False
    username = "Offline"
    servers = 0
    users = 0
    members = []




def update_status(name, server_count, user_count):

    global online
    global username
    global servers
    global users


    online = True
    username = name
    servers = server_count
    users = user_count





def get_status():

    return (

        online,

        "Online" if online else "Offline",

        username,

        servers,

        users

    )





def update_members(bot):

    global members


    members = []


    for guild in bot.guilds:

        for member in guild.members:

            if not member.bot:

                members.append({

                    "id": str(member.id),

                    "name": member.name

                })





def get_members():

    return members