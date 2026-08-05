import os
from dotenv import load_dotenv
from google import genai


load_dotenv()


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


MODEL = "gemini-3.1-flash-lite"



def analyze_image(image_file):

    try:

        uploaded = client.files.upload(
            file=image_file
        )


        response = client.models.generate_content(

            model=MODEL,

            contents=[
                uploaded,
                """
                You are Javris.
                Describe this image naturally.
                Talk like a person, not a robot.
                """
            ]

        )


        return response.text


    except Exception as e:

        print("VISION ERROR:", e)

        return "I couldn't understand that image."