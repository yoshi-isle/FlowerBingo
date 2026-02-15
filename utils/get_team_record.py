import asyncpg


async def get_team_record(conn: asyncpg.Connection, discord_user_id: str):
    try:
        player_row = await conn.fetchrow(
            "SELECT * FROM public.players WHERE discord_id = $1",
            str(discord_user_id),
        )
        if not player_row:
            return None

        team_row = await conn.fetchrow(
            "SELECT * FROM public.teams WHERE id = $1", player_row["team_id"]
        )

        return team_row

    except Exception as e:
        print(f"Error getting team information`: {e}")
