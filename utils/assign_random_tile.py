import asyncpg


async def assign_random_tile(conn: asyncpg.Connection, team_id: int, category: int):
    """Assign a random tile to a team for the specified category, avoiding the last 3 completed tiles"""
    # Check if team already has an active tile for this category
    existing_assignment = await conn.fetchrow(
        "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND category = $2 AND is_active = $3",
        team_id,
        category,
        True,
    )

    if existing_assignment:
        raise ValueError(f"Team already has a tile assignment for category {category}")

    # Get the last 10 completed tiles for this team and category (k=10 approach)
    last_completed_tiles = await conn.fetch(
        """
        SELECT tile_id FROM public.tile_assignments 
        WHERE team_id = $1 AND category = $2 AND is_active = false 
        ORDER BY created_at DESC 
        LIMIT 10
        """,
        team_id,
        category,
    )
    
    # Extract tile IDs to exclude from the next assignment
    excluded_tile_ids = [record["tile_id"] for record in last_completed_tiles]

    # Get a random tile for this category, excluding the last 3 completed
    tile = await _get_random_tile(conn, category, excluded_tile_ids)

    # Create the tile assignment
    tile_assignment = await conn.fetchrow(
        """
        INSERT INTO public.tile_assignments 
        (team_id, tile_id, is_active, category, remaining_submissions, created_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        RETURNING *
        """,
        team_id,
        tile["id"],
        True,
        tile["category"],
        tile["completion_counter"],
    )

    return tile_assignment



async def _get_random_tile(conn: asyncpg.Connection, category: int, excluded_tile_ids: list = None):
    """Get a random tile for the specified category, excluding specified tile IDs"""
    if excluded_tile_ids:
        tile = await conn.fetchrow(
            "SELECT * FROM public.tiles WHERE category = $1 AND id != ALL($2) ORDER BY RANDOM() LIMIT 1",
            category,
            excluded_tile_ids,
        )
    else:
        tile = await conn.fetchrow(
            "SELECT * FROM public.tiles WHERE category = $1 ORDER BY RANDOM() LIMIT 1",
            category,
        )
    
    if not tile:
        raise ValueError(f"No tiles found for category {category}")
    return tile