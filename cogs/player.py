import os
import discord
from discord import app_commands
from discord.ext import commands

from constants import Emojis
from embeds.submission import get_submission_embed
from utils.get_board_payload import get_board_payload
from utils.create_submission import create_submission
from utils.get_team_record import get_team_record
from utils.get_team_tiles import get_team_tiles
from utils.get_tile_definition import get_tile_definition


class PlayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="board", description="View the board for your team")
    async def view_board(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            async with self.bot.db_pool.acquire() as conn:
                team = await get_team_record(conn, str(interaction.user.id))

                # Guard - no team found for the player
                if not team:
                    await interaction.edit_original_response(
                        content="Looks like you're not part of any team. Please contact an admin."
                    )
                    return

                # Guard - wrong channel
                if int(team["discord_channel_id"]) != interaction.channel_id:
                    await interaction.edit_original_response(
                        content="You can only use `/board` in your team's channel."
                    )
                    return

                team_embed, file = await get_board_payload(
                    conn,
                    team["id"],
                    team=team,
                )
                await interaction.edit_original_response(
                    embed=team_embed, attachments=[file]
                )
        except Exception as e:
            print(f"Error getting board for {interaction.user.display_name}", e)
            await interaction.edit_original_response(
                content="Error getting your board. Please contact an admin"
            )

    async def submit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[int]]:
        try:
            team = await get_team_record(self.bot.db_pool, str(interaction.user.id))
            if not team:
                return []

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
        if not team:
            await interaction.response.send_message(
                "Looks like you're not part of any team. Please contact an admin."
            )
            return

        # Guard - wrong channel
        if int(team["discord_channel_id"]) != interaction.channel_id:
            await interaction.response.send_message(
                content="You can only use `/submit` in your team's channel."
            )
            return

        tile = await get_tile_definition(
            conn=self.bot.db_pool, team_id=team["id"], category=option
        )

        __submission_channel_id = os.getenv("PENDING_SUBMISSIONS_CHANNEL_ID")
        __player_channel_id = team["discord_channel_id"]

        # Get the relevant channels
        player_team_channel = self.bot.get_channel(int(__player_channel_id))
        admin_channel = self.bot.get_channel(int(__submission_channel_id))

        receipt_embed, submission_embed = get_submission_embed(interaction, tile, team)

        __player_embed_message = await player_team_channel.send(embed=receipt_embed)
        __admin_embed_message = await admin_channel.send(embed=submission_embed)

        await create_submission(
            conn=self.bot.db_pool,
            discord_id=interaction.user.id,
            category=option,
            player_embed_id=__player_embed_message.id,
            admin_embed_id=__admin_embed_message.id,
        )

        # Add reactions to admin embed
        await __admin_embed_message.add_reaction(Emojis.THUMBS_UP)
        await __admin_embed_message.add_reaction(Emojis.NO)
        await __admin_embed_message.add_reaction(Emojis.FORCE)
        await __admin_embed_message.add_reaction(Emojis.EXPLAIN)

        await interaction.response.send_message(
            f"Your submission has been sent! {Emojis.THUMBS_UP} Please wait for an admin to approve.",
            ephemeral=True,
        )

    @app_commands.command(name="explain", description="Explain what counts for a tile")
    @app_commands.autocomplete(option=submit_autocomplete)
    async def explain(self, interaction: discord.Interaction, option: int):

        # Guard - not signed up
        team = await get_team_record(self.bot.db_pool, interaction.user.id)
        if not team:
            await interaction.response.send_message(
                "Looks like you're not part of any team. Please contact an admin."
            )
            return

        # Guard - wrong channel
        if int(team["discord_channel_id"]) != interaction.channel_id:
            await interaction.response.send_message(
                content="You can only use `/explain` in your team's channel."
            )
            return

        # Get tile
        tile = await get_tile_definition(self.bot.db_pool, team["id"], option)
        if not tile:
            await interaction.response.send_message(
                "Error getting the tile information. Please contact an admin."
            )

        embed = discord.Embed(title=tile["tile_name"], colour=0xFFFFFF)

        embed.add_field(
            name="OSRS Wiki Link",
            value=tile["wiki_url"],
            inline=False,
        )
        embed.add_field(
            name="What counts for this tile?",
            value=tile["eligible_drops"],
            inline=False,
        )

        embed.set_thumbnail(
            url="https://oldschool.runescape.wiki/images/Cake_of_guidance.png?de576"
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
