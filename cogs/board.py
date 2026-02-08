import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from utils.get_team_board import get_team_board
from utils.image_gen.board import generate_image


class BoardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="board", description="View the board for your team")
    async def view_board(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            async with self.bot.db_pool.acquire() as conn:
                board = await get_team_board(conn, str(interaction.user.id))
                img = await asyncio.to_thread(generate_image, board)
                await interaction.followup.send(
                    file=discord.File(img, filename="board.png")
                )
        except Exception:
            await interaction.followup.send(content="Error getting your board.")


async def setup(bot):
    await bot.add_cog(BoardCog(bot))
