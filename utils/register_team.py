import asyncpg

from utils.assign_random_tile import assign_random_tile

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
