import asyncpg


async def get_team_board(conn: asyncpg.Connection, discord_user_id: str):
    try:
        player_row = await conn.fetchrow(
            "SELECT team_id FROM public.players WHERE discord_id = $1",
            discord_user_id,
        )
        team_row = await conn.fetchrow(
            "SELECT id FROM public.teams WHERE id = $1", player_row["team_id"]
        )

        return await get_team_tiles(conn, team_row["id"])

    except Exception as e:
        print(f"Error getting team board`: {e}")


async def get_team_tiles(conn: asyncpg.Connection, team_id):
    tile_info = []
    tile_raw_data = []

    for category in [1, 2, 3, 4]:
        tile_assignment = await conn.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND is_active = $2 AND category = $3",
            team_id,
            True,
            category,
        )

        if tile_assignment:
            tile = await conn.fetchrow(
                "SELECT * FROM public.tiles WHERE id = $1", tile_assignment["tile_id"]
            )

            if tile:
                tile_view = {
                    "tile_name": tile["tile_name"],
                    "category": tile["category"],
                    "remaining_submissions": tile_assignment["remaining_submissions"],
                    "description": tile["description"],
                    "image_data": tile["image_data"],
                }

                tile_info.append(tile_view)
                tile_raw_data.append(tile)

    return tile_info
