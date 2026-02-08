import discord
from discord import app_commands
from discord.ext import commands

from utils.get_global_state import get_global_state


class HelloCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Test bot responsiveness")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @app_commands.command(name="dbtest", description="Test database connection")
    async def dbtest(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            global_state = await get_global_state(self.bot.db_pool)
            if not global_state.get("is_game_running", False):
                await interaction.followup.send(
                    "The game has not started yet, so you can't do that."
                )
        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")


async def setup(bot):
    await bot.add_cog(HelloCog(bot))
