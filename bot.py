import discord
import os
import asyncio
import asyncpg
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
GAME_NOT_RUNNING_MESSAGE = "The game is not running yet. The game will start <t:1772841600:R>"


async def is_game_running() -> bool:
    try:
        async with bot.db_pool.acquire() as conn:
            is_running = await conn.fetchval(
                """
                SELECT COALESCE(is_game_running, false)
                FROM public.global_game_states
                ORDER BY id ASC
                LIMIT 1
                """
            )
            return bool(is_running)
    except Exception as e:
        print(f"Error checking game state: {e}")
        return False


@bot.check
async def global_prefix_command_check(ctx: commands.Context) -> bool:
    if await is_game_running():
        return True

    await ctx.send(GAME_NOT_RUNNING_MESSAGE)
    return False


@bot.tree.interaction_check
async def global_interaction_check(interaction: discord.Interaction) -> bool:
    if await is_game_running():
        return True

    if interaction.response.is_done():
        await interaction.followup.send(GAME_NOT_RUNNING_MESSAGE, ephemeral=True)
    else:
        await interaction.response.send_message(GAME_NOT_RUNNING_MESSAGE, ephemeral=True)
    return False


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Loaded {len(bot.cogs)} cog(s)")
    await bot.tree.sync()
    print("Slash commands synced")


async def create_db_pool():
    """
    Create PostgreSQL async database connection pool
    """
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
