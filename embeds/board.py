from discord import Embed

from constants import Emojis


def get_board_embed(team, board):
    embed = Embed(title=team["team_name"])

    embed.color = 0x00FF00
    embed.set_thumbnail(
        url="https://oldschool.runescape.wiki/images/thumb/3rd_age_pickaxe_detail.png/300px-3rd_age_pickaxe_detail.png?0bf61"
    )
    embed.set_footer(text="Need help? Use /explain for more clarity.")

    embed.add_field(
        name=f"{Emojis.HIGHSCORES} 1st place",
        value="70 points",
        inline=False,
    )
    embed.add_field(
        name=f"__{board[0].get('tile_name', 'Error')}__",
        value=f"* Submissions Remaining: {board[0].get('remaining_submissions', 'Error')}\n* Re-roll: <t:1771116840:R>",
        inline=False,
    )
    embed.add_field(
        name=f"__{board[1].get('tile_name', 'Error')}__",
        value=f"* Submissions Remaining: {board[1].get('remaining_submissions', 'Error')}\n* Re-roll: <t:1771116840:R>",
        inline=False,
    )
    embed.add_field(
        name=f"__{board[2].get('tile_name', 'Error')}__",
        value=f"* Submissions Remaining: {board[2].get('remaining_submissions', 'Error')}\n* Re-roll: <t:1771116840:R>",
        inline=False,
    )
    embed.add_field(
        name=f"__{board[3].get('tile_name', 'Error')}__",
        value=f"* Submissions Remaining: {board[3].get('remaining_submissions', 'Error')}\n* Re-roll: <t:1771116840:R>",
        inline=False,
    )

    return embed
