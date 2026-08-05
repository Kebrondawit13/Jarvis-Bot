import os
import aiohttp

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")


async def search_gif(query):

    if not GIPHY_API_KEY:
        return None

    url = "https://api.giphy.com/v1/gifs/search"

    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": 1,
        "rating": "pg"
    }

    async with aiohttp.ClientSession() as session:

        async with session.get(
            url,
            params=params
        ) as response:

            data = await response.json()

            if data["data"]:
                return data["data"][0]["images"]["original"]["url"]

    return None