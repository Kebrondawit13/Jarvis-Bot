import requests
import os


API_KEY = os.getenv("GEMINI_API_KEY")


def check_message(text):

    try:

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": API_KEY
        }


        data = {

            "contents": [

                {
                    "parts": [

                        {
                            "text": f"""
Check this Discord message for:

- hate speech
- threats
- harassment
- extreme insults
- sexual content involving minors
- dangerous content

Message:

{text}

Reply only:

YES

or

NO
"""
                        }

                    ]

                }

            ]

        }


        r = requests.post(
            url,
            headers=headers,
            json=data
        )


        result = r.json()


        answer = result["candidates"][0]["content"]["parts"][0]["text"]


        return "YES" in answer.upper()


    except Exception as e:

        print("Moderation error:", e)

        return False