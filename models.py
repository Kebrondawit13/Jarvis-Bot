from google import genai
from dotenv import load_dotenv
import os


load_dotenv()


api_key = os.getenv("GEMINI_API_KEY")


if not api_key:
    raise Exception("GEMINI_API_KEY missing")


client = genai.Client(
    api_key=api_key
)


try:

    print("Available models:\n")

    for model in client.models.list():
        print(model.name)


except Exception as e:

    print("Model list error:")
    print(e)