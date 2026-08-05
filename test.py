import os
from dotenv import load_dotenv
from google import genai


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")


print("Gemini key loaded:", api_key is not None)


if not api_key:
    raise Exception("GEMINI_API_KEY missing")


client = genai.Client(
    api_key=api_key
)


MODEL = "gemini-3.1-flash-lite"


try:

    response = client.models.generate_content(
        model=MODEL,
        contents="Hello Gemini, are you working?"
    )


    print("\nGemini Response:")
    print(response.text)


except Exception as e:

    print("\nGemini Error:")
    print(e)