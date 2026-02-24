import asyncpg

async def _check_flower_basket(conn: asyncpg.Connection):
    game_state = await conn.fetchrow(
        """
        SELECT *
        FROM public.global_game_states
        ORDER BY id ASC
        LIMIT 1
        FOR UPDATE
        """
    )

    if not game_state:
        return False

    if game_state["is_flower_basket_active"]:
        flower_basket_tile_id = await conn.fetchval(
            """
            SELECT *
            FROM public.tiles
            WHERE category = 5 AND id = $1
            """, game_state["flower_basket_tile_id"])
        if flower_basket_tile_id:
            tile = await conn.fetchrow(
                """
                SELECT * FROM public.tiles WHERE Id = $1
                """,
                flower_basket_tile_id,
            )
            return tile
        
async def get_team_tiles(conn: asyncpg.Connection, team_id):
    tile_info = []

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

            tile_view = {
                "tile_name": tile["tile_name"],
                "category": tile["category"],
                "remaining_submissions": tile_assignment["remaining_submissions"],
                "description": tile["description"],
                "image_data": tile["image_data"],
            }

            tile_info.append(tile_view)
    
    basket = await _check_flower_basket(conn)
    if basket:
        tile_view = {
                "tile_name": basket["tile_name"],
                "category": 5,
                "remaining_submissions": 1,
                "description": basket["description"],
                "image_data": basket["image_data"],
            }
        tile_info.append(tile_view)


    return tile_info
