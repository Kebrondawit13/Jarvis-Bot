from flask import Flask, render_template_string, request
import memory
import bot_status


app = Flask(__name__)


memory.setup()



HOME_HTML = """

<!DOCTYPE html>

<html>

<head>

<title>Javris AI Dashboard</title>


<style>

body {

background:#111;
color:white;
font-family:Arial;
padding:30px;

}


.card {

background:#222;
padding:20px;
margin:15px 0;
border-radius:15px;

}


a {

color:#00ff88;
text-decoration:none;
font-size:18px;

}


button,input {

padding:10px;
border-radius:8px;
border:none;

}

</style>


</head>


<body>


<h1>🤖 Javris-AI Dashboard</h1>



<div class="card">

<h2>Bot Status</h2>

<h3 style="color:#00ff88">

🟢 {{status}}

</h3>


<p>Bot: {{name}}</p>

<p>Servers: {{servers}}</p>

<p>Users: {{users}}</p>

<p>Total Messages: {{messages}}</p>


</div>





<div class="card">


<h2>👥 Users</h2>



{% for user in members %}


<div class="card">


<a href="/user/{{user['id']}}">

👤 {{user['name']}}

</a>


</div>


{% endfor %}



</div>





<div class="card">


<h2>🔎 Search Messages</h2>


<form action="/search">


<input 

name="q"

placeholder="Search"

>


<button>

Search

</button>


</form>


</div>



</body>

</html>

"""





HISTORY_HTML = """

<!DOCTYPE html>

<html>

<head>


<title>User History</title>


<style>


body {

background:#111;

color:white;

font-family:Arial;

padding:30px;

}



.message {

background:#222;

padding:15px;

margin:10px;

border-radius:10px;

}



.user {

color:#00ff88;

}



.ai {

color:#00aaff;

}



a {

color:#00ff88;

}


</style>


</head>



<body>


<h1>💬 {{username}}'s Chat History</h1>




{% if history|length == 0 %}


<h2>No messages found</h2>


{% endif %}





{% for msg in history %}



<div class="message">



{% if msg[0] == "user" %}


<h3 class="user">

👤 User

</h3>


{% else %}


<h3 class="ai">

🤖 Javris-AI

</h3>


{% endif %}




<p>

{{msg[1]}}

</p>



<small>

{{msg[2]}}

</small>



</div>



{% endfor %}




<br>


<a href="/">

⬅ Back

</a>


</body>


</html>

"""






SEARCH_HTML = """

<!DOCTYPE html>

<html>

<body style="background:#111;color:white;font-family:Arial;padding:30px">



<h1>🔎 Search Results</h1>




{% for r in results %}



<div style="background:#222;padding:20px;margin:10px;border-radius:15px">



<a style="color:#00ff88;font-size:20px"

href="/user/{{r[0]}}">


👤 {{r[1]}}


</a>



</div>



{% endfor %}




<br>


<a href="/" style="color:#00ff88">

⬅ Back

</a>



</body>

</html>

"""









@app.route("/")
def home():


    status = bot_status.get_status()


    members = bot_status.get_members()


    total_messages = memory.get_message_count()



    return render_template_string(

        HOME_HTML,


        status=status[1],


        name=status[2],


        servers=status[3],


        users=status[4],


        messages=total_messages,


        members=members

    )









@app.route("/user/<uid>")
def user(uid):


    history = memory.get_history(uid)


    username = "Unknown User"



    for member in bot_status.get_members():


        if member["id"] == uid:


            username = member["name"]

            break





    return render_template_string(

        HISTORY_HTML,


        history=history,


        username=username

    )









@app.route("/search")
def search():


    q = request.args.get("q","")



    results = memory.search_messages(q)



    return render_template_string(

        SEARCH_HTML,


        results=results

    )









app.run(

    host="0.0.0.0",

    port=5000

)