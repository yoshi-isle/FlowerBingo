import asyncio
from datetime import timedelta

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

    # Get all reroll timers

    reroll_timers = []
    assignments_created_at = await conn.fetch(
        "SELECT created_at FROM public.tile_assignments WHERE team_id = $1 AND is_active = true ORDER BY category asc",
        team_id
    )
    config_names = ["easy_reroll_hours", "medium_reroll_hours", "hard_reroll_hours", "elite_reroll_hours"]
    for i in range(4):

        reroll_config = await conn.fetchval(
            "SELECT amount FROM global_configs WHERE name = $1",
            config_names[i]
        )

        created_at = assignments_created_at[i][0]

        # Add reroll_config hours
        created_at += timedelta(hours=reroll_config)

        # Convert it to fancy discord <T:23342:R> or whatever for relative
        reroll_timer = f"<t:{int(created_at.timestamp())}:R>"
        reroll_timers.append(reroll_timer)
    

    # Get reroll configuration from db
    img = await asyncio.to_thread(generate_image, board)
    embed = get_board_embed(team_record, board, reroll_timers)
    file = discord.File(fp=img, filename="board.png")

    return embed, file
