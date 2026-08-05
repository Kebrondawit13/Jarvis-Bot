# Javris AI Discord Bot

Javris is a Discord AI bot made with Python.

It uses Gemini AI for conversations and includes features like memory, image generation, vision, file reading, GIF reactions, moderation, and admin controls.

## Features

- AI chat with Gemini
- User memory system using SQLite
- Image generation
- Image analysis
- PDF/file support
- GIF reactions
- Moderation tools
- Auto chat modes
- Slash commands
- Web dashboard
- Owner-only settings

## Setup

### 1. Install requirements

Make sure you have Python installed.

Install the required libraries:

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

Create a file named:

```
.env
```

in the same folder as `bot.py`.

Copy the format from `.env.example`:

```env
DISCORD_TOKEN=your_discord_token
GEMINI_API_KEY=your_gemini_api_key
GIPHY_API_KEY=your_giphy_api_key
OWNER_ID=your_discord_user_id
```

Replace the values with your own keys.

## Run the bot

```bash
python bot.py
```

## Commands

### AI Commands

```
/ai - Chat with Javris
/ask - Ask a question
/image - Generate an image
/vision - Analyze an image
/file - Ask about a file
/clear - Clear your memory
/status - View bot status
```

### Owner Commands

```
/admin_toggle_autochat
/admin_toggle_gif
/admin_add_channel
/admin_remove_channel
/admin_clear_all_memory
```

## Files

```
bot.py            Main bot
text_ai.py        Gemini AI system
vision_ai.py      Image analysis
image_ai.py       Image generation
gif_ai.py         GIF system
file_ai.py        File handling
memory.py         Database memory
moderation.py     Moderation
dashboard.py      Web dashboard
```

## Notes

- Keep your `.env` file private.
- Never upload your bot token or API keys.
- The bot stores memory locally using SQLite.

## Made by

Kebrondawit13