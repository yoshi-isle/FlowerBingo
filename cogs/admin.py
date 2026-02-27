import discord
from discord import app_commands
from discord.ext import commands


from constants import Emojis
from utils.get_board_payload import get_board_payload
from utils.register_team import assign_random_tile

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="admin_force_spawn",
        description="[ADMIN] Force spawn a tile for the team in this channel if none exists.",
    )
    @app_commands.choices(difficulty=[app_commands.Choice(name="Wildflower (+10)", value=1),
                app_commands.Choice(name="Rose (+50)", value=2),
                app_commands.Choice(name="Tulip (+200)", value=3),
                app_commands.Choice(name="Orchid (+400)", value=4),])
    
    async def force_spawn(self, interaction: discord.Interaction, difficulty: int):
        await interaction.response.defer(thinking=True)
        try:
            async with self.bot.db_pool.acquire() as conn:
                team = await conn.fetchrow(
                    "SELECT * FROM public.teams WHERE discord_channel_id = $1",
                    str(interaction.channel_id),
                )

                if not team:
                    await interaction.followup.send(
                        "No team is registered for this channel."
                    )
                    return

                existing_assignment = await conn.fetchrow(
                    "SELECT * FROM public.tile_assignments WHERE team_id = $1 AND category = $2 AND is_active = true",
                    team["id"],
                    difficulty,
                )

                if existing_assignment:
                    await interaction.followup.send(
                        "This team already has an active tile for this category."
                    )
                    return

                new_assignment = await assign_random_tile(conn, team["id"], difficulty)
                tile = await conn.fetchrow(
                    "SELECT tile_name FROM public.tiles WHERE id = $1",
                    new_assignment["tile_id"],
                )

                tile_name = tile["tile_name"] if tile else "Unknown tile"
                await interaction.followup.send(
                    f"{Emojis.THUMBS_UP} Spawned {difficulty} tile for {team['team_name']}: {tile_name}"
                )

        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")

    @app_commands.command(name="admin_rollback", description="[ADMIN] EMERGENCIES ONLY. Rollback a submission that was approved incorrectly.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def admin_rollback(self, interaction: discord.Interaction, submission_id: int):
        try:
            async with self.bot.db_pool.acquire() as conn:
                assignment = await conn.fetchrow(
                    "SELECT team_id FROM public.tile_assignments WHERE id = $1",
                    submission_id
                )
                team = await conn.fetchrow(
                    "SELECT team_name FROM public.teams WHERE id = $1",
                    assignment["team_id"]
                )

                # Fetch the most recent assignment for this team and set it to inactive
                most_recent = await conn.execute(
                    "UPDATE public.tile_assignments SET is_active = false WHERE team_id = $1 AND category = $2 LIMIT 1 RETURNING id",
                    assignment["team_id"],
                    assignment.get("category")
                )

                # Rollback the tile assignment with the given submission_id
                await conn.execute(
                    "UPDATE public.tile_assignments SET is_active = true WHERE id = $1",
                    submission_id
                )
                
                await interaction.response.send_message(f"✅ [ADMIN] Performed an emergency rollback. Undid tile assignment {most_recent} and re-activated #{submission_id} for this team: {team['team_name']}")
        except Exception as e:
            print(e)

    @app_commands.command(name="admin_reveal", description="[ADMIN] Reveal a board for the team in this channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def admin_reveal(self, interaction: discord.Interaction):
        try:
            channel_id = interaction.channel.id
            async with self.bot.db_pool.acquire() as conn:
                team = await conn.fetchrow(
                    "SELECT * FROM public.teams WHERE discord_channel_id = $1",
                    str(channel_id)
                )
                if not team:
                    await interaction.response.send_message("No team found for this channel.")
                    return
                team_embed, file = await get_board_payload(
                    conn,
                    team["id"],
                    team=team,
                )
                await interaction.response.send_message(embed=team_embed, file=file)
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
