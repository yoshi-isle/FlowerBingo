from discord import Embed


def get_board_embed(team, board):
    embed = Embed(title=team["team_name"])

    print(len(board))

    embed.add_field(
        name="Wildflower (+10)",
        value=f"{board[0].get('tile_name', 'Error')}\nSubmissions Needed: {board[0].get('remaining_submissions', 'Error')}",
        inline=False,
    )
    embed.add_field(
        name="Tulip (+30)",
        value=f"{board[1].get('tile_name', 'Error')}\nSubmissions Needed: {board[1].get('remaining_submissions', 'Error')}",
        inline=False,
    )
    embed.add_field(
        name="Rose (+100)",
        value=f"{board[2].get('tile_name', 'Error')}\nSubmissions Needed: {board[2].get('remaining_submissions', 'Error')}",
        inline=False,
    )
    embed.add_field(
        name="Orchid (+350)",
        value=f"{board[3].get('tile_name', 'Error')}\nSubmissions Needed: {board[3].get('remaining_submissions', 'Error')}",
        inline=False,
    )

    return embed
