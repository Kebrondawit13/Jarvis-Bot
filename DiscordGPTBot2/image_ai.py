import requests
import urllib.parse


def generate_image(prompt):

    encoded = urllib.parse.quote(prompt)

    url = (
        "https://image.pollinations.ai/prompt/"
        + encoded
    )

    try:

        response = requests.get(
            url,
            timeout=120
        )

        if response.status_code == 200:

            filename = "javris_image.png"

            with open(filename, "wb") as f:
                f.write(response.content)

            return filename

        else:

            print("IMAGE ERROR:", response.text)
            return None


    except Exception as e:

        print("IMAGE ERROR:", e)
        return None