import discord
from discord import app_commands
from discord.ext import commands


class SubmissionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="submit_tile", description="Submit your drop")
    async def submit_tile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            await interaction.followup.send(content="TODO - create submission")
        except Exception:
            await interaction.followup.send(content="Error submitting.")


async def setup(bot):
    await bot.add_cog(SubmissionCog(bot))
