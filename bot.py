import discord
from discord.ext import commands
import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Loaded {len(bot.cogs)} cog(s)")
    # Sync slash commands
    await bot.tree.sync()
    print("Slash commands synced")


async def create_db_pool():
    """Create database connection pool"""
    bot.db_pool = await asyncpg.create_pool(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        min_size=10,
        max_size=20,
    )
    print("Database pool created")


async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded cog: {filename}")


async def main():
    async with bot:
        await create_db_pool()
        await load_cogs()
        try:
            await bot.start(os.getenv("DISCORD_TOKEN"))
        finally:
            # Clean up pool on shutdown
            await bot.db_pool.close()
            print("Database pool closed")


if __name__ == "__main__":
    asyncio.run(main())
