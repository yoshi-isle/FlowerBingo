import asyncpg

from utils.get_assignment import get_assignment
from utils.get_player import get_player
from utils.get_team_record import get_team_record


async def approve_submission(
    conn: asyncpg.Connection,
    discord_id: int,
    category: int,
    player_embed_id: int,
    admin_embed_id: int,
):
    try:
        player = await get_player(conn, str(discord_id))
        # Get the tile assignment from the user
        team = await get_team_record(conn, str(discord_id))
        print(player, team)
        # Get the tile data from the category
        assignment = await get_assignment(conn, team["id"], category)

        # Create the tile submission
        await conn.fetchrow(
            """INSERT INTO tile_submissions 
                (created_at,
                player_id,
                is_approved,
                admin_receipt_message_id,
                receipt_message_id,
                tile_assignment_id) 
            VALUES (NOW(), $1, false, $2, $3, $4)""",
            player["id"],
            str(admin_embed_id),
            str(player_embed_id),
            assignment["id"],
        )

    except Exception as e:
        print(f"Error getting team information`: {e}")
        raise e
