import asyncpg


async def get_random_tile(conn: asyncpg.Connection, category: int):
    """Get a random tile for the specified category"""
    tile = await conn.fetchrow(
        "SELECT * FROM public.tiles WHERE category = $1 ORDER BY RANDOM() LIMIT 1",
        category,
    )
    if not tile:
        raise ValueError(f"No tiles found for category {category}")
    return tile


async def assign_random_tile(conn: asyncpg.Connection, team_id: int, category: int):
    """Assign a random tile to a team for the specified category"""
    # Check if team already has an active tile for this category
    existing_assignment = await conn.fetchrow(
        "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND category = $2 AND is_active = $3",
        team_id,
        category,
        True,
    )

    if existing_assignment:
        raise ValueError(f"Team already has a tile assignment for category {category}")

    # Get a random tile for this category
    tile = await get_random_tile(conn, category)

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


async def register_team(conn: asyncpg.Connection, team_name: str, channel_id: int):
    """Register a new team and assign 4 random tiles (one for each category)"""
    try:
        # Insert the team and get the ID
        team = await conn.fetchrow(
            "INSERT INTO public.teams (team_name, discord_channel_id, created_at) VALUES ($1, $2, NOW()) RETURNING id",
            team_name,
            str(channel_id),
        )
        team_id = team["id"]

        # Assign random tiles for categories 1-4
        for category in [1, 2, 3, 4]:
            await assign_random_tile(conn, team_id, category)

        return team_id

    except Exception as e:
        print(f"Error registering team: {e}")
        raise
