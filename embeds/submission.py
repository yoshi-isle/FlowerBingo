from discord import Color, Embed
import discord

from constants import Emojis


def get_submission_embed(interaction: discord.Interaction, tile, team) -> tuple:
    """
    Player submission receipt
    """
    player_receipt = Embed(title="", colour=Color.yellow())
    player_receipt.set_author(
        name=f"Tile Submission by {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url,
    )
    player_receipt.add_field(
        name="Status", value="🟡 Waiting for approval", inline=False
    )
    player_receipt.add_field(
        name="I completed...", value=f"{tile['tile_name']}\n", inline=False
    )

    """
    Admin submission receipt
    """
    admin_receipt = Embed(title="", colour=Color.yellow())
    admin_receipt.set_author(
        name=f"Tile Submission by {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url,
    )
    admin_receipt.add_field(
        name="Status", value="🟡 Waiting for approval", inline=False
    )
    admin_receipt.add_field(
        name="I completed...", value=f"{tile['tile_name']}\n", inline=False
    )

    admin_receipt.add_field(
        name="Team",
        value=f"{team['team_name']} {interaction.channel.jump_url}\n",
        inline=False,
    )
    admin_receipt.set_footer(text="Please be careful when approving submissions 📋")

    # Return both
    return player_receipt, admin_receipt
