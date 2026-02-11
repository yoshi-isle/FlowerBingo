import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands

from embeds.board import get_board_embed
from embeds.submission import get_submission_embed
from utils.get_team_record import get_team_record
from utils.get_team_tiles import get_team_tiles
from utils.get_tile_by_category import get_tile_assignment_by_category
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
        team = await get_team_record(self.bot.db_pool, interaction.user.id)
        tile = await get_tile_assignment_by_category(self.bot.db_pool, team_id=team["id"], category=option)

        __submission_channel_id = os.getenv("PENDING_SUBMISSIONS_CHANNEL_ID")
        __player_channel_id = team["discord_channel_id"]
        
        # Get the relevant channels
        player_team_channel = self.bot.get_channel(int(__player_channel_id))
        admin_channel = self.bot.get_channel(int(__submission_channel_id))

        receipt_embed, submission_embed = get_submission_embed(interaction, tile, team)

        __player_embed_message = await player_team_channel.send(embed=receipt_embed)
        __admin_embed_message = await admin_channel.send(embed=submission_embed)

        # Add reactions to admin embed
        await __admin_embed_message.add_reaction("✅")
        await __admin_embed_message.add_reaction("❌")

        await interaction.response.send_message("Your submission has been sent! ✅ Please wait for an admin to approve.", ephemeral=True)

    @app_commands.command(name="explain", description="Explain what counts for a tile")
    @app_commands.autocomplete(option=submit_autocomplete)
    async def explain(self, interaction: discord.Interaction, option: int):
        # TODO - Proof of concept

        embed = discord.Embed(title="3 Different Moons Equipment",
                      colour=0xffffff)

        embed.add_field(name="OSRS Wiki Link",
                        value="https://oldschool.runescape.wiki/w/Lunar_Chest",
                        inline=False)
        embed.add_field(name="What counts for this tile?",
                        value="Any (3) different pieces of Moons Equipment. Eclipse atlatl, Eclipse moon helm, Eclipse moon chestplate, Eclipse moon tassets, Dual macuahuitl, Blood moon helm, Blood moon chestplate, Blood moon tassets, Blue moon spear, Blue moon helm, Blue moon chestplate, Blue moon tassets",
                        inline=False)

        embed.set_thumbnail(url="https://oldschool.runescape.wiki/images/Cake_of_guidance.png?de576")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
