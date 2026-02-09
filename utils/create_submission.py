import asyncpg


async def create_submission(conn: asyncpg.Connection, discord_id, tile_id: int):
    try:
        # Get the tile assignment from the user
        player = await conn.fetchrow(
            "SELECT team_id from players WHERE discord_id = $1", str(discord_id)
        )
        tile_assignment = await conn.fetchrow(
            "SELECT * from tile_assignments WHERE team_id = $1 AND category = $2",
            player["team_id"],
            tile_id,
        )

        # Create the tile submission
        print(tile_assignment)

    except Exception as e:
        print(f"Error getting team information`: {e}")
