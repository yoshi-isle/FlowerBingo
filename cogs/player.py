import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

from embeds.board import get_board_embed
from embeds.submission import get_submission_embed
from utils.create_submission import create_submission
from utils.get_team_record import get_team_record
from utils.get_team_tiles import get_team_tiles
from utils.image_gen.board import generate_image


class PlayerCog(commands.Cog):
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

    async def submit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        try:
            team = await get_team_record(self.bot.db_pool, str(interaction.user.id))
            tiles = await get_team_tiles(self.bot.db_pool, team["id"])

            choices = []

            if not tiles:
                return []

            for i, tile in enumerate(tiles):
                choices.append(
                    app_commands.Choice(
                        name=tile.get("tile_name", "Unknown Tile"), value=i + 1
                    )
                )

            return choices

        except Exception as e:
            print(f"Error in submit autocomplete: {e}")
            return []

    @app_commands.command(name="submit", description="Submit a tile")
    @app_commands.autocomplete(option=submit_autocomplete)
    async def submit(self, interaction: discord.Interaction, option: int):
        team = await get_team_record(interaction.user.id)
        submission_embed = get_submission_embed(interaction, option, team)
        admin_channel = self.bot.get_channel(
            int(os.getenv("PENDING_SUBMISSIONS_CHANNEL_ID"))
        )
        await admin_channel.send(embed=submission_embed)
        # get the tile id from the option
        await create_submission(self.bot.db_pool, interaction.user.id, option)
        pass


async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
