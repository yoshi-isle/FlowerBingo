import asyncio

import discord

from embeds.board import get_board_embed
from utils.get_team_points import get_team_points
from utils.get_team_tiles import get_team_tiles
from utils.image_gen.board import generate_image


async def get_board_payload(conn, team_id, team=None):
    team_record = team
    if not team_record:
        team_record = await conn.fetchrow(
            "SELECT * FROM public.teams WHERE id = $1",
            team_id,
        )

    if not team_record:
        return None, None

    board = await get_team_tiles(conn, team_id)
    points = await get_team_points(conn, team_id)

    img = await asyncio.to_thread(generate_image, board)
    embed = get_board_embed(team_record, board, points)
    file = discord.File(fp=img, filename="board.png")

    return embed, file
