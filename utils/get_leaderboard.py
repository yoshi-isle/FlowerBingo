import asyncpg


async def get_leaderboard(conn: asyncpg.Connection):
    category_point_ratio = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    try:
        config_row = await conn.fetchrow(
            """
            SELECT easy_points, medium_points, hard_points, elite_points
            FROM public.global_configs
            LIMIT 1
            """
        )

        easy_points = int(config_row["easy_points"] or 0) if config_row else 0
        medium_points = int(config_row["medium_points"] or 0) if config_row else 0
        hard_points = int(config_row["hard_points"] or 0) if config_row else 0
        elite_points = int(config_row["elite_points"] or 0) if config_row else 0

        category_point_ratio = {
            1: easy_points,
            2: medium_points,
            3: hard_points,
            4: elite_points,
        }

        rows = await conn.fetch(
            """
            SELECT
                t.id AS team_id,
                t.team_name,
                COALESCE(SUM(
                    CASE
                        WHEN ta.is_active = false
                             AND COALESCE(ta.was_skipped, false) = false
                        THEN CASE ta.category
                            WHEN 1 THEN $1
                            WHEN 2 THEN $2
                            WHEN 3 THEN $3
                            WHEN 4 THEN $4
                            ELSE 0
                        END
                        ELSE 0
                    END
                ), 0) AS points,
                COUNT(*) FILTER (
                    WHERE ta.is_active = false
                      AND COALESCE(ta.was_skipped, false) = false
                ) AS completed_tiles,
                COUNT(*) FILTER (
                    WHERE ta.is_active = false
                      AND COALESCE(ta.was_skipped, false) = true
                ) AS skipped_tiles,
                COUNT(*) FILTER (WHERE ta.is_active = true) AS active_tiles
            FROM public.teams t
            LEFT JOIN public.tile_assignments ta ON ta.team_id = t.id
            GROUP BY t.id, t.team_name
            ORDER BY points DESC, t.team_name ASC
            """,
            easy_points,
            medium_points,
            hard_points,
            elite_points,
        )

        leaderboard = []
        leaderboard_map = {}

        for row in rows:
            points = int(row["points"] or 0)
            completed_tiles = int(row["completed_tiles"] or 0)
            skipped_tiles = int(row["skipped_tiles"] or 0)
            active_tiles = int(row["active_tiles"] or 0)

            leaderboard.append(
                {
                    "team_id": row["team_id"],
                    "team_name": row["team_name"],
                    "points": points,
                    "completed_tiles": completed_tiles,
                    "skipped_tiles": skipped_tiles,
                    "active_tiles": active_tiles,
                }
            )
            leaderboard_map[row["team_name"]] = {
                "points": points,
                "completed_tiles": completed_tiles,
                "skipped_tiles": skipped_tiles,
                "active_tiles": active_tiles,
            }

        sorted_map = dict(
            sorted(
                leaderboard_map.items(),
                key=lambda item: (item[1]["points"], item[0]),
                reverse=True,
            )
        )

        return leaderboard, sorted_map, category_point_ratio

    except Exception as e:
        print(f"Error getting leaderboard`: {e}")
        return [], {}, category_point_ratio
