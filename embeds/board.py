from discord import Embed

from constants import Emojis


def get_board_embed(team, board, reroll_timers, is_flower_basket_active, flower_basket_tile=None):
    embed = Embed(title=team['team_name'])

    if team.get('color_hex', None):
        embed.color = int(team['color_hex'].replace("#", ""), 16)
    else:
        embed.color = 0xFFB6C1
        
    if team.get('image_url', None):
        embed.set_thumbnail(url=team['image_url'])
    else:
        embed.set_thumbnail(
            url="https://oldschool.runescape.wiki/images/thumb/3rd_age_pickaxe_detail.png/300px-3rd_age_pickaxe_detail.png?0bf61"
        )
    embed.set_footer(text="Use /explain to see what counts")
    points = [5,50,200,400,999]
    board_len = min(4, len(board), len(reroll_timers))
    for i in range(board_len):
        embed.add_field(
            name=f"{board[i].get('tile_name', 'Error')} (`{board[i].get('remaining_submissions', 'Error')}` remaining)",
            value=f"Re-roll: {reroll_timers[i]}",
            inline=False,
        )
    
    if is_flower_basket_active:
        flower_basket_name = (
            flower_basket_tile["tile_name"]
            if flower_basket_tile
            else "Unknown tile"
        )
        embed.add_field(
            name=f"💮 {flower_basket_name} (`{flower_basket_tile.get('remaining_submissions', 'Error')}` remaining)",
            value=f"Expiration timer: {reroll_timers[4]}",
            inline=False,
        )

    return embed
