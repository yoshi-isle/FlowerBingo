import discord
from discord import app_commands
from discord.ext import commands
import asyncio

from utils.get_team_tiles import get_team_tiles
from utils.get_team_record import get_team_record
from utils.image_gen.board import generate_image

from embeds.board import get_board_embed


class BoardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="board", description="View the board for your team")
    async def view_board(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            async with self.bot.db_pool.acquire() as conn:
                team = await get_team_record(conn, str(interaction.user.id))
                board = await get_team_tiles(conn, team["id"])

                img = await asyncio.to_thread(generate_image, board)
                team_embed = get_board_embed(team, board)

                file = discord.File(fp=img, filename="board.png")
                await interaction.edit_original_response(
                    embed=team_embed, attachments=[file]
                )
        except Exception as e:
            await interaction.edit_original_response(
                content=f"Error getting your board: {e}"
            )


async def setup(bot):
    await bot.add_cog(BoardCog(bot))
