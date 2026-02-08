import asyncpg


async def get_global_state(conn: asyncpg.Connection):
    try:
        global_game_states = await conn.fetchrow(
            "SELECT * from public.global_game_states"
        )
        return global_game_states

    except Exception as e:
        print(f"Error getting global game state`: {e}")
