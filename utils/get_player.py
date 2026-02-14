import asyncpg


async def get_player(conn: asyncpg.Connection, discord_user_id: str):
    player_row = await conn.fetchrow(
        "SELECT * FROM public.players WHERE discord_id = $1",
        str(discord_user_id),
    )
    return player_row
