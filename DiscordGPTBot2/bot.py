import os
import time
import glob
import inspect
import logging
import asyncio
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

import bot_status
import vision_ai
import file_ai
import moderation
import text_ai
import gif_ai

from image_ai import generate_image

load_dotenv()

# =========================
# LOGGING
# =========================

logging.basicConfig(
    filename="javris.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# CONFIG & SECURITY
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise Exception("DISCORD_TOKEN missing from .env")

raw_owner_id = os.getenv("OWNER_ID")
if not raw_owner_id:
    raise Exception("OWNER_ID missing from .env")

try:
    OWNER_ID = int(raw_owner_id)
except ValueError:
    raise Exception("OWNER_ID must be a valid integer Discord ID")

GUILD_ID = os.getenv("DEV_GUILD_ID")

bot_status.setup()

# =========================
# GLOBALS & CONCURRENCY
# =========================

cooldowns = {}
GIF_COOLDOWN = {}
CHANNEL_COOLDOWN = {}
ACTIVE_USERS = set()
COOLDOWN_SECONDS = 3
CHANNEL_COOLDOWN_SECONDS = 2

AUTO_CHAT_ENABLED = False
GIF_ENABLED = True
AUTO_CHAT_PREFIX = "javris"
AI_CHANNELS = set()

ALLOWED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp"
}

# =========================
# TEMP FILES
# =========================

TEMP_DIR = "temp_images"
os.makedirs(TEMP_DIR, exist_ok=True)

def clean_temp_files():
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        for file in glob.glob(os.path.join(TEMP_DIR, ext)):
            try:
                os.remove(file)
            except Exception as e:
                logging.error(f"Temp cleanup error for {file}: {e}")

clean_temp_files()

# =========================
# DATABASE & SETTINGS (ASYNC SINGLETON POOL)
# =========================

DB_PATH = "javris_memory.db"
_db_connection = None
_db_lock = asyncio.Lock()

async def get_db():
    global _db_connection
    async with _db_lock:
        if _db_connection is None:
            _db_connection = await aiosqlite.connect(DB_PATH)
            await _db_connection.execute("PRAGMA journal_mode=WAL")
            await _db_connection.execute("PRAGMA synchronous=NORMAL")
            await _db_connection.execute("PRAGMA busy_timeout=10000")
        return _db_connection

async def init_db():
    db = await get_db()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS memory(
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp REAL
        )
        """
    )
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS memory_user_index
        ON memory(user_id)
        """
    )
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS memory_time_index
        ON memory(timestamp)
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_channels(
            channel_id INTEGER PRIMARY KEY
        )
        """
    )
    await db.commit()

async def load_settings():
    global AUTO_CHAT_ENABLED, GIF_ENABLED, AI_CHANNELS
    db = await get_db()
    async with db.execute("SELECT value FROM settings WHERE key = 'autochat_enabled'") as cursor:
        row = await cursor.fetchone()
        if row:
            AUTO_CHAT_ENABLED = (row[0] == "1")

    async with db.execute("SELECT value FROM settings WHERE key = 'gif_enabled'") as cursor:
        row = await cursor.fetchone()
        if row:
            GIF_ENABLED = (row[0] == "1")

    async with db.execute("SELECT channel_id FROM ai_channels") as cursor:
        rows = await cursor.fetchall()
        AI_CHANNELS = {row[0] for row in rows}

async def save_setting(key, value):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    await db.commit()

async def add_ai_channel_db(channel_id):
    db = await get_db()
    await db.execute("INSERT OR IGNORE INTO ai_channels (channel_id) VALUES (?)", (channel_id,))
    await db.commit()

async def remove_ai_channel_db(channel_id):
    db = await get_db()
    await db.execute("DELETE FROM ai_channels WHERE channel_id = ?", (channel_id,))
    await db.commit()

async def cleanup_old_memory(days=180):
    db = await get_db()
    cutoff = time.time() - (60 * 60 * 24 * days)
    cursor = await db.execute("DELETE FROM memory WHERE timestamp < ?", (cutoff,))
    deleted = cursor.rowcount

    await db.execute(
        """
        DELETE FROM memory
        WHERE rowid NOT IN (
            SELECT rowid FROM memory
            ORDER BY timestamp DESC
            LIMIT 100000
        )
        """
    )

    await db.commit()
    return max(deleted, 0)

async def vacuum_db():
    db = await get_db()
    await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    await db.execute("VACUUM")

@tasks.loop(hours=48)
async def memory_cleanup_loop():
    deleted = await cleanup_old_memory(days=180)
    if deleted > 0:
        logging.info(f"Automated DB Cleanup: Pruned {deleted} old records.")

@memory_cleanup_loop.before_loop
async def before_memory_cleanup():
    await bot.wait_until_ready()

# =========================
# CLIENT / BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class JavrisBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await init_db()
        await load_settings()
        await cleanup_old_memory()

        if not memory_cleanup_loop.is_running():
            memory_cleanup_loop.start()

        if not cache_cleanup_loop.is_running():
            cache_cleanup_loop.start()

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} slash commands instantly to dev guild {GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands globally.")

    async def close(self):
        global _db_connection
        if _db_connection:
            await _db_connection.close()
            _db_connection = None

        logging.info("Javris shutting down cleanly.")
        print("Javris shutting down cleanly.")
        await super().close()

bot = JavrisBot()

# =========================
# SLASH COMMAND ERROR HANDLER
# =========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logging.error(f"Slash command error: {error}")
    if not interaction.response.is_done():
        try:
            await interaction.response.send_message("❌ Javris error.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass
    else:
        try:
            await interaction.followup.send("❌ Javris error.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

# =========================
# COOLDOWNS & CACHE
# =========================

def cleanup_cooldowns():
    now = time.time()
    for key in list(cooldowns):
        if now - cooldowns[key] > 60:
            del cooldowns[key]

    for user_id in list(GIF_COOLDOWN):
        if now - GIF_COOLDOWN[user_id] > 60:
            del GIF_COOLDOWN[user_id]

    for channel_id in list(CHANNEL_COOLDOWN):
        if now - CHANNEL_COOLDOWN[channel_id] > 60:
            del CHANNEL_COOLDOWN[channel_id]

@tasks.loop(hours=24)
async def cache_cleanup_loop():
    cleanup_cooldowns()

def is_rate_limited(user_id, command):
    cleanup_cooldowns()
    now = time.time()
    key = (user_id, command)
    last = cooldowns.get(key, 0)

    if now - last < COOLDOWN_SECONDS:
        return True

    cooldowns[key] = now
    return False

def is_channel_rate_limited(channel_id):
    now = time.time()
    last = CHANNEL_COOLDOWN.get(channel_id, 0)
    if now - last < CHANNEL_COOLDOWN_SECONDS:
        return True
    CHANNEL_COOLDOWN[channel_id] = now
    return False

# =========================
# MEMORY FUNCTIONS
# =========================

async def get_user_memory(user_id, limit=20):
    db = await get_db()
    async with db.execute(
        """
        SELECT role, content
        FROM memory
        WHERE user_id = ?
        ORDER BY timestamp ASC
        """,
        (user_id,)
    ) as cursor:
        rows = await cursor.fetchall()

    rows = rows[-limit:]
    return [{"role": row[0], "content": row[1]} for row in rows]

async def add_user_memory(user_id, role, content):
    db = await get_db()
    await db.execute(
        """
        INSERT INTO memory
        (user_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, role, content, time.time())
    )

    await db.execute(
        """
        DELETE FROM memory
        WHERE user_id = ?
        AND rowid NOT IN
        (
            SELECT rowid FROM
            (
                SELECT rowid
                FROM memory
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 40
            )
        )
        """,
        (user_id, user_id)
    )
    await db.commit()

async def clear_user_memory(user_id):
    db = await get_db()
    cursor = await db.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount
    await db.commit()
    return deleted > 0

async def clear_all_memory():
    db = await get_db()
    cursor = await db.execute("DELETE FROM memory")
    deleted = cursor.rowcount
    await db.commit()
    return max(deleted, 0)

# =========================
# HELPERS
# =========================

async def send_long(target, text, embed=None):
    if not text and not embed:
        return

    if text:
        text = text.replace("@everyone", "@ everyone").replace("@here", "@ here")

    CHUNK_SIZE = 1900

    if isinstance(target, discord.Interaction):
        if text:
            for i in range(0, len(text), CHUNK_SIZE):
                chunk = text[i:i+CHUNK_SIZE]
                is_last_chunk = (i + CHUNK_SIZE >= len(text))
                current_embed = embed if is_last_chunk else None
                if not target.response.is_done():
                    await target.response.send_message(
                        chunk,
                        embed=current_embed,
                        allowed_mentions=discord.AllowedMentions.none()
                    )
                else:
                    await target.followup.send(
                        chunk,
                        embed=current_embed,
                        allowed_mentions=discord.AllowedMentions.none()
                    )
        elif embed:
            if not target.response.is_done():
                await target.response.send_message(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            else:
                await target.followup.send(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none()
                )
    else:
        if text:
            for i in range(0, len(text), CHUNK_SIZE):
                chunk = text[i:i+CHUNK_SIZE]
                is_last_chunk = (i + CHUNK_SIZE >= len(text))
                current_embed = embed if is_last_chunk else None
                await target.send(
                    chunk,
                    embed=current_embed,
                    allowed_mentions=discord.AllowedMentions.none()
                )
        elif embed:
            await target.send(
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none()
            )

async def run_moderation_check(message):
    try:
        check = getattr(moderation, "check_message", None)
        if check is None:
            return False

        if inspect.iscoroutinefunction(check):
            return await check(message)

        return await asyncio.to_thread(check, message)
    except Exception as e:
        logging.error(f"Moderation error: {e}")
        return False

# =========================
# DISCORD EVENTS
# =========================

@bot.event
async def on_disconnect():
    logging.warning("Discord gateway disconnected")

@bot.event
async def on_resumed():
    logging.info("Discord connection resumed")

@bot.event
async def on_error(event, *args, **kwargs):
    logging.error(f"Discord error {event}: {args}")

# =========================
# BOT READY
# =========================

@bot.event
async def on_ready():
    total_users = sum(guild.member_count or 0 for guild in bot.guilds)

    bot_status.update_status(str(bot.user), len(bot.guilds), total_users)
    bot_status.update_members(bot)

    print("========================")
    print(f"Logged in as {bot.user}")
    print(f"Owner ID: {OWNER_ID}")
    print("Javris Online")
    print(f"Servers: {len(bot.guilds)}")
    print(f"Users: {total_users}")
    print("========================")

# =========================
# AI CHAT CORE
# =========================

async def execute_chat(user, guild, prompt, enable_gif=True):
    if len(prompt) > 4000:
        return "❌ Message too long.", None

    roles = []
    if isinstance(user, discord.Member):
        roles = [r.name for r in user.roles if r.name != "@everyone"]

    role_text = ", ".join(roles) if roles else "No roles"
    guild_name = guild.name if guild and hasattr(guild, "name") else "DM"

    personality = f"""You are Javris, a smart Discord companion.

Personality:
- Smart like Jarvis.
- Friendly & casual.
- Can joke and match the user's energy.
- Do not sound like customer support.

Rules:
- Do not introduce yourself every message.
- Do not say "How can I help you today?"
- Do not mention AI models unless asked.

User Info:
Username: {user.name}
Display Name: {user.display_name}
ID: {user.id}
Server: {guild_name}
Roles: {role_text}

If asked who created you:
"I was created by my developer to be Javris, a smart Discord companion."
"""

    user_id = user.id
    history = await get_user_memory(user_id, 20)

    messages = [{"role": "system", "content": personality}]
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    ask_primary = getattr(text_ai, "ask_text_ai", None)
    if not ask_primary:
        return "❌ AI engine configuration error.", None

    try:
        reply = await asyncio.wait_for(
            asyncio.to_thread(ask_primary, messages),
            timeout=60
        )

        if reply:
            await add_user_memory(user_id, "user", prompt)
            await add_user_memory(user_id, "assistant", reply)

        gif_url = None
        if enable_gif and GIF_ENABLED and reply:
            now = time.time()
            last_gif_time = GIF_COOLDOWN.get(user_id, 0)

            if now - last_gif_time >= 10:
                try:
                    gif_prompt_system = """You choose reaction GIFs for Javris.

Analyze:
- User message
- Javris reply
- Emotion
- Situation

Return ONLY a GIPHY search phrase.

Examples:
happy -> celebration dance
funny -> laughing reaction
sad -> comforting hug

If no GIF is needed return:
NONE"""

                    gif_prompt = await asyncio.to_thread(
                        text_ai.ask_text_ai,
                        [
                            {"role": "system", "content": gif_prompt_system},
                            {
                                "role": "user",
                                "content": f"User message: {prompt}\n\nJavris reply: {reply}"
                            }
                        ]
                    )

                    if gif_prompt:
                        gif_prompt = gif_prompt.lower().strip()
                        if gif_prompt not in ["none", "none.", "no", "no gif"]:
                            logging.info(f"GIF SEARCH: {gif_prompt}")
                            GIF_COOLDOWN[user_id] = now
                            gif_url = await asyncio.wait_for(
                                gif_ai.search_gif(gif_prompt),
                                timeout=10
                            )
                except asyncio.TimeoutError:
                    logging.warning("GIF search timed out")
                except Exception as e:
                    logging.error(f"GIF AI error: {e}")

        return reply, gif_url

    except asyncio.TimeoutError:
        return "⏱ Javris timed out.", None
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return "❌ Javris encountered an error.", None

async def chat(message, prompt):
    if message.author.id in ACTIVE_USERS:
        await message.channel.send("⏳ I'm still answering your last message.", allowed_mentions=discord.AllowedMentions.none())
        return

    if is_channel_rate_limited(message.channel.id):
        return

    ACTIVE_USERS.add(message.author.id)
    try:
        async with message.channel.typing():
            reply, gif_url = await execute_chat(message.author, message.guild, prompt, enable_gif=True)

        embed = None
        if gif_url:
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_image(url=gif_url)

        await send_long(message.channel, reply, embed=embed)
    finally:
        ACTIVE_USERS.discard(message.author.id)

# =========================
# SLASH COMMANDS
# =========================

@bot.tree.command(name="ai", description="Talk with Javris AI")
@app_commands.describe(prompt="Your message to Javris")
async def slash_ai(interaction: discord.Interaction, prompt: str):
    if is_rate_limited(interaction.user.id, "ai"):
        await interaction.response.send_message("⏳ Please wait a few seconds.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    if interaction.user.id in ACTIVE_USERS:
        await interaction.response.send_message("⏳ I'm still answering your last message.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    ACTIVE_USERS.add(interaction.user.id)
    await interaction.response.defer()

    try:
        try:
            reply, gif_url = await execute_chat(interaction.user, interaction.guild, prompt, enable_gif=True)
        except Exception as e:
            logging.error(e)
            reply = "❌ Javris crashed."
            gif_url = None

        embed = None
        if gif_url:
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_image(url=gif_url)

        await send_long(interaction, reply, embed=embed)
    finally:
        ACTIVE_USERS.discard(interaction.user.id)

@bot.tree.command(name="ask", description="Ask Javris a quick question")
@app_commands.describe(question="Question for Javris")
async def slash_ask(interaction: discord.Interaction, question: str):
    if is_rate_limited(interaction.user.id, "ask"):
        await interaction.response.send_message("⏳ Please wait.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    await interaction.response.defer()
    try:
        reply, _ = await execute_chat(interaction.user, interaction.guild, question, enable_gif=False)
    except Exception as e:
        logging.error(e)
        reply = "❌ Javris crashed."
    await send_long(interaction, reply)

@bot.tree.command(name="file", description="Ask Javris about a file")
@app_commands.describe(request="File request")
async def slash_file(interaction: discord.Interaction, request: str):
    if is_rate_limited(interaction.user.id, "file"):
        await interaction.response.send_message("⏳ Please wait a few seconds.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    await interaction.response.defer()
    try:
        result = await asyncio.to_thread(file_ai.handle_file, request)
    except Exception as e:
        result = f"File error: {e}"

    await send_long(interaction, result)

@bot.tree.command(name="image", description="Generate an AI image")
@app_commands.describe(prompt="Image description")
async def slash_image(interaction: discord.Interaction, prompt: str):
    if is_rate_limited(interaction.user.id, "image"):
        await interaction.response.send_message("⏳ Please wait a few seconds.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    await interaction.response.defer()
    path = None
    try:
        path = await asyncio.to_thread(generate_image, prompt)
    except Exception as e:
        logging.error(f"Image generation error: {e}")
        path = None
    finally:
        if path and os.path.exists(path):
            try:
                await interaction.followup.send("🖼 Here you go:", file=discord.File(path, filename="javris_image.png"), allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                logging.error(f"Failed to send image followup: {e}")
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass
        else:
            await interaction.followup.send("❌ Image generation failed.", allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="vision", description="Analyze an image")
@app_commands.describe(attachment="Image")
async def slash_vision(interaction: discord.Interaction, attachment: discord.Attachment):
    if is_rate_limited(interaction.user.id, "vision"):
        await interaction.response.send_message("⏳ Please wait a few seconds.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    content_type = attachment.content_type or ""
    if not content_type.startswith("image/"):
        await interaction.response.send_message("❌ Only images allowed.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    await interaction.response.defer()
    try:
        result = await asyncio.to_thread(vision_ai.analyze_image, attachment.url)
    except Exception as e:
        logging.error(f"Vision error: {e}")
        result = "❌ Failed to analyze image."

    await send_long(interaction, result)

@bot.tree.command(name="clear", description="Clear your memory")
async def slash_clear(interaction: discord.Interaction):
    await clear_user_memory(interaction.user.id)
    await interaction.response.send_message("🧹 Memory cleared.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="status", description="Javris status")
async def slash_status(interaction: discord.Interaction):
    status = bot_status.get_status()
    text = f"""🤖 **Javris Status**

Servers: {status[3]}
Users: {status[4]}
Security Lock: Disabled
Auto Chat: {"Enabled" if AUTO_CHAT_ENABLED else "Disabled"}
GIFs: {"Enabled" if GIF_ENABLED else "Disabled"}
AI Channels: {len(AI_CHANNELS)}

Features:
✅ AI Chat | ✅ GIF AI | ✅ Image AI | ✅ Vision AI | ✅ File AI | ✅ Memory
"""
    await interaction.response.send_message(text, allowed_mentions=discord.AllowedMentions.none())

# =========================
# WELCOME GIF SYSTEM
# =========================

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if not channel:
        return

    gif = None
    if GIF_ENABLED:
        try:
            gif = await asyncio.wait_for(
                gif_ai.search_gif("epic welcome new member discord celebration"),
                timeout=10
            )
        except Exception as e:
            logging.error(f"Welcome GIF error: {e}")

    embed = None
    if gif:
        embed = discord.Embed(color=discord.Color.green())
        embed.set_image(url=gif)

    try:
        await channel.send(
            content=f"🎉 Welcome {member.mention} to {member.guild.name}!",
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none()
        )
    except Exception as e:
        logging.error(f"Welcome message send error: {e}")

# =========================
# MESSAGE HANDLER & AUTO CHAT
# =========================

@bot.event
async def on_message(message):
    global AUTO_CHAT_ENABLED, GIF_ENABLED

    if message.author.bot:
        return

    content_lower = message.content.lower().strip()

    # --- AUTO CHAT TRIGGERS ---

    # Trigger 1: Direct Mention (@Javris)
    if bot.user in message.mentions:
        prompt = message.clean_content
        if bot.user:
            prompt = prompt.replace(f"@{bot.user.display_name}", "").strip()
        if prompt:
            if is_rate_limited(message.author.id, "ai"):
                await message.channel.send("⏳ Please wait a few seconds.", allowed_mentions=discord.AllowedMentions.none())
                return
            await chat(message, prompt)
            return

    # Trigger 2: Replying to Javris's message
    if message.reference:
        try:
            replied = await message.channel.fetch_message(message.reference.message_id)
            if replied.author == bot.user and message.content.strip():
                if is_rate_limited(message.author.id, "ai"):
                    await message.channel.send("⏳ Please wait a few seconds.", allowed_mentions=discord.AllowedMentions.none())
                    return
                await chat(message, message.content.strip())
                return
        except Exception:
            pass

    # Trigger 3: Word boundary prefix ("javris hi" vs "javrisbot hi")
    if content_lower == AUTO_CHAT_PREFIX or content_lower.startswith(AUTO_CHAT_PREFIX + " "):
        prompt = message.content[len(AUTO_CHAT_PREFIX):].strip()
        if prompt:
            if is_rate_limited(message.author.id, "ai"):
                await message.channel.send("⏳ Please wait a few seconds.", allowed_mentions=discord.AllowedMentions.none())
                return
            await chat(message, prompt)
            return

    # Trigger 4: Dedicated AI Channels
    if message.channel.id in AI_CHANNELS and message.content.strip():
        if is_rate_limited(message.author.id, "ai"):
            await message.channel.send("⏳ Please wait a few seconds.", allowed_mentions=discord.AllowedMentions.none())
            return
        await chat(message, message.content.strip())
        return

    # Trigger 5: Global Auto Chat mode (if enabled)
    if AUTO_CHAT_ENABLED and message.content.strip():
        if is_rate_limited(message.author.id, "ai"):
            return
        await chat(message, message.content.strip())
        return

    # --- PREFIX COMMANDS FALLBACK ---
    await bot.process_commands(message)

# =========================
# OWNER / ADMIN COMMANDS
# =========================

@bot.tree.command(name="admin_toggle_autochat", description="Toggle global auto-chat mode (Owner only)")
async def admin_toggle_autochat(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    global AUTO_CHAT_ENABLED
    AUTO_CHAT_ENABLED = not AUTO_CHAT_ENABLED
    await save_setting("autochat_enabled", "1" if AUTO_CHAT_ENABLED else "0")
    await interaction.response.send_message(f"⚙️ Global Auto-Chat is now **{'Enabled' if AUTO_CHAT_ENABLED else 'Disabled'}**.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="admin_toggle_gif", description="Toggle GIF integration (Owner only)")
async def admin_toggle_gif(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    global GIF_ENABLED
    GIF_ENABLED = not GIF_ENABLED
    await save_setting("gif_enabled", "1" if GIF_ENABLED else "0")
    await interaction.response.send_message(f"⚙️ GIF Integration is now **{'Enabled' if GIF_ENABLED else 'Disabled'}**.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="admin_add_channel", description="Add current channel to AI channels (Owner only)")
async def admin_add_channel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    channel_id = interaction.channel.id
    AI_CHANNELS.add(channel_id)
    await add_ai_channel_db(channel_id)
    await interaction.response.send_message(f"⚙️ Channel <#{channel_id}> added to dedicated AI channels.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="admin_remove_channel", description="Remove current channel from AI channels (Owner only)")
async def admin_remove_channel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    channel_id = interaction.channel.id
    if channel_id in AI_CHANNELS:
        AI_CHANNELS.remove(channel_id)
    await remove_ai_channel_db(channel_id)
    await interaction.response.send_message(f"⚙️ Channel <#{channel_id}> removed from dedicated AI channels.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

@bot.tree.command(name="admin_clear_all_memory", description="Wipe global conversation memory database (Owner only)")
async def admin_clear_all_memory(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())
        return

    deleted_count = await clear_all_memory()
    await vacuum_db()
    await interaction.response.send_message(f"🧹 Successfully wiped global database memory ({deleted_count} records removed & database vacuumed).", ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.critical(f"Critical startup error: {e}")