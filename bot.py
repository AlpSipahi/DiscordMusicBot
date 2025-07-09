import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()

logger = setup_logger()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    logger.critical("DISCORD_BOT_TOKEN is not set in the .env file.")
    raise ValueError("Bot token not found in .env file")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("Bot is ready.")
    print("Type a terminal command: channels, changechannel, transcribe, roles, exit")

    transcriber = bot.get_cog("Transcriber")
    if transcriber:
        bot.loop.create_task(transcriber.listen_for_terminal_commands())
    else:
        logger.warning("Transcriber cog not found on bot.")

    roles_cog = bot.get_cog("Roles")
    if roles_cog:
        bot.loop.create_task(roles_cog.listen_for_terminal_commands())
    else:
        logger.warning("Roles cog not found on bot.")

async def main():
    async with bot:
        await bot.load_extension("cogs.music")
        await bot.load_extension("cogs.transcriber")
        await bot.load_extension("cogs.roles")  # Load roles cog
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown via keyboard interrupt.")
