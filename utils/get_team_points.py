import asyncpg


async def get_team_points(conn: asyncpg.Connection, team_id):
    category_point_ratio = {
        1: 10,
        2: 40,
        3: 100,
        4: 280,
    }

    try:
        tile_assignments = await conn.fetch(
            "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND is_active = $2",
            team_id,
            False,
        )

        return int(
            sum(
                category_point_ratio.get(tile_assignment["category"], 0)
                for tile_assignment in tile_assignments
            )
        )

    except Exception as e:
        print(f"Error getting team points`: {e}")
        return 0
