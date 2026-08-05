import os
from dotenv import load_dotenv
from google import genai


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")


client = genai.Client(
    api_key=api_key
)


MODEL = "gemini-3.1-flash-lite"



def ask_text_ai(messages):


    prompt = ""


    for msg in messages:

        role = msg.get("role")
        content = msg.get("content")


        if role == "system":

            prompt += (
                "SYSTEM:\n"
                + content
                + "\n\n"
            )


        elif role == "user":

            prompt += (
                "USER:\n"
                + content
                + "\n\n"
            )



    try:


        response = client.models.generate_content(

            model=MODEL,

            contents=prompt

        )


        return response.text



    except Exception as e:


        print(
            "Gemini Error:",
            e
        )


        return "❌ Javris is offline right now."