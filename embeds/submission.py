from discord import Color, Embed
import discord


def get_submission_embed(interaction: discord.Interaction, tile, team) -> tuple:
    receipt_embed = Embed(title="", colour=Color.yellow())
    receipt_embed.set_author(
        name=f"Tile Submission by {interaction.user.display_name}",
        icon_url=interaction.user.display_avatar.url,
    )
    receipt_embed.add_field(
        name="Status", value="🟡 Waiting for approval", inline=False
    )
    receipt_embed.add_field(
        name="I completed...", value=f"{tile['tile_name']}\n", inline=False
    )
    admin_embed = receipt_embed.copy()
    admin_embed.add_field(
        name="Team",
        value=f"{team['team_name']} {interaction.channel.jump_url}\n",
        inline=False,
    )
    admin_embed.set_footer(text="Please be careful when approving submissions 📋")
    return receipt_embed, admin_embed
