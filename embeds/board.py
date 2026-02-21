from discord import Embed

from constants import Emojis


def get_board_embed(team, board, reroll_timers, is_flower_basket_active):
    embed = Embed(title=team['team_name'])

    embed.color = 0xFFB6C1
    embed.set_thumbnail(
        url="https://oldschool.runescape.wiki/images/thumb/3rd_age_pickaxe_detail.png/300px-3rd_age_pickaxe_detail.png?0bf61"
    )
    embed.set_footer(text="Use /explain to see what counts")
    for i in range(4):
        embed.add_field(
            name=f"{board[i].get('tile_name', 'Error')} (`{board[i].get('remaining_submissions', 'Error')}` remaining)",
            value=f"Re-roll: {reroll_timers[i]}",
            inline=False,
        )
    
    if is_flower_basket_active:
        embed.add_field(
            name="💮 Flower Basket 💮",
            value="There's a flower basket active!",
            inline=False,
        )

    return embed
