import asyncpg


async def get_tile_definition(conn: asyncpg.Connection, team_id: int, category: int):
    """
    Assignment = team's individual progress. "How many remain"
    Tile = Raw data for the tile
    """
    try:
        assignment = await conn.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND category = $2 AND is_active = true",
            team_id,
            category,
        )

        tile = await conn.fetchrow(
            "SELECT * FROM public.tiles WHERE id = $1",
            assignment["tile_id"],
        )

        return tile

    except Exception as e:
        print(f"Error getting tile assignment`: {e}")
