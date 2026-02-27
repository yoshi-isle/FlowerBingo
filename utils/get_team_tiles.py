import asyncpg
        
async def get_team_tiles(conn: asyncpg.Connection, team_id):
    tile_info = []

    for category in [1, 2, 3, 4, 5]:
        tile_assignment = await conn.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND is_active = $2 AND category = $3",
            team_id,
            True,
            category,
        )

        if not tile_assignment and category in [1, 2, 3, 4]:
            names = {
                1: "Wildflower (+10)",
                2: "Rose (+50)",
                3: "Tulip (+200)",
                4: "Orchid (+400)",
            }
            raise ValueError(f"The team is missing a slot for category: {names[category]}. Use `/admin_force_spawn {names[category]}` to fix it. <@726237123857874975>")

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

    return tile_info
