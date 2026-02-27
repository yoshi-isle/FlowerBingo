import asyncio
from datetime import timedelta, datetime, timezone

import discord

from embeds.board import get_board_embed
from utils.get_global_state import get_global_state
from utils.get_team_tiles import get_team_tiles
from utils.image_gen.board import generate_image


async def get_board_payload(conn, team_id, team=None, new_tile_index=None):
    team_record = team
    if not team_record:
        team_record = await conn.fetchrow(
            "SELECT * FROM public.teams WHERE id = $1",
            team_id,
        )

    if not team_record:
        return None, None

    game_state = await get_global_state(conn)
    is_flower_basket_active = bool(
        game_state and game_state["is_flower_basket_active"]
    )
    
    try:
        board = await get_team_tiles(conn, team_id)
    except ValueError as e:
        return str(e), None

    # Get all reroll timers
    reroll_timers = []
    assignments_created_at = await conn.fetch(
        "SELECT category, created_at FROM public.tile_assignments WHERE team_id = $1 AND is_active = true AND category BETWEEN 1 AND 4",
        team_id,
    )
    assignment_created_at_by_category = {
        row["category"]: row["created_at"] for row in assignments_created_at
    }

    config_names = ["easy_reroll_hours", "medium_reroll_hours", "hard_reroll_hours", "elite_reroll_hours"]
    for i in range(4):

        reroll_config = await conn.fetchval(
            "SELECT amount FROM public.global_configs WHERE name = $1",
            config_names[i]
        )

        created_at = assignment_created_at_by_category.get(i + 1)
        if created_at is None or reroll_config is None:
            reroll_timers.append("N/A")
            continue

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)

        # Add reroll_config hours
        created_at += timedelta(hours=reroll_config)

        # Convert it to fancy discord <T:23342:R> or whatever for relative
        reroll_timer = f"<t:{int(created_at.timestamp())}:R>"
        if datetime.now(timezone.utc) > created_at:
            reroll_timers.append("**You can re-roll!**")
        else:
            reroll_timers.append(reroll_timer)

    # Todo - Future me will have a hard time understanding this
    flower_basket_tile = None
    if len(board) == 5:
        flower_basket_tile = board[4]
        reroll_timer = f"<t:{int(game_state['flower_basket_expires'].timestamp())}:R>"
        reroll_timers.append(reroll_timer)

    # Get reroll configuration from db
    img = await asyncio.to_thread(
        generate_image,
        board,
        new_tile_index,
        is_flower_basket_active,
        flower_basket_tile
    )
    embed = get_board_embed(
        team_record,
        board,
        reroll_timers,
        is_flower_basket_active,
        flower_basket_tile,
    )
    file = discord.File(fp=img, filename="board.png")

    return embed, file
