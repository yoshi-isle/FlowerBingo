import discord
from discord import app_commands
from discord.ext import commands


from constants import Emojis
from utils.get_team_record import get_team_record
from utils.register_team import assign_random_tile
from utils.register_team import register_team


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="admin_register_team", description="Register a new team (IN THIS CHANNEL)"
    )
    async def admin_register_team(
        self, interaction: discord.Interaction, team_name: str
    ):
        try:
            async with self.bot.db_pool.acquire() as conn:
                team_id = await register_team(conn, team_name, interaction.channel_id)

            await interaction.response.send_message(
                f"{Emojis.THUMBS_UP} Team '{team_name}' (ID: {team_id}) has been registered with 4 random tiles by {interaction.user.mention}. This channel ID {interaction.channel_id} is used in their team record."
            )
        except Exception as e:
            await interaction.response.send_message(f"Database error: {str(e)}")

    async def team_autocomplete(self, interaction: discord.Interaction, current: str):
        """
        Autocomplete callback for team names
        """
        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT team_name FROM public.teams WHERE team_name ILIKE $1",
                    f"%{current}%",
                )
                return [
                    app_commands.Choice(name=row["team_name"], value=row["team_name"])
                    for row in rows
                ]
        except Exception:
            return []

    @app_commands.command(
        name="admin_register_player", description="Register a player to a team"
    )
    @app_commands.autocomplete(team_name=team_autocomplete)
    async def admin_register_player(
        self, interaction: discord.Interaction, player: discord.User, team_name: str
    ):
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get team_id from team_name
                team_row = await conn.fetchrow(
                    "SELECT id FROM public.teams WHERE team_name = $1", team_name
                )

                if not team_row:
                    await interaction.response.send_message(
                        f"Team '{team_name}' not found."
                    )
                    return

                existing_team = await get_team_record(conn, str(player))
                if existing_team:
                    await interaction.response.send_message(
                        f"That player is already on a team: {existing_team['team_name']}"
                    )
                    return

                team_id = team_row["id"]

                # Insert player into database
                await conn.execute(
                    "INSERT INTO public.players (discord_id, team_id, created_at) VALUES ($1, $2, NOW())",
                    str(player.id),
                    team_id,
                )

            await interaction.response.send_message(
                f"{Emojis.THUMBS_UP} Player {player.mention} has been registered to team '{team_name}'."
            )
        except Exception as e:
            await interaction.response.send_message(f"Database error: {str(e)}")

    @app_commands.command(
        name="admin_unregister_player", description="Removes a player from their team"
    )
    async def admin_unregister_player(
        self, interaction: discord.Interaction, player: discord.User
    ):
        try:
            async with self.bot.db_pool.acquire() as conn:
                existing_team = await get_team_record(conn, str(player.id))
                if not existing_team:
                    await interaction.response.send_message(
                        "That player is not on any team."
                    )
                    return

                # Remove player from database
                await conn.execute(
                    "DELETE FROM public.players WHERE discord_id = $1",
                    str(player.id),
                )

            await interaction.response.send_message(
                f"{Emojis.THUMBS_UP} Player {player.mention} has been unregistered from  their team '{existing_team['team_name']}'."
            )
        except Exception as e:
            await interaction.response.send_message(f"Database error: {str(e)}")

    @app_commands.command(
        name="admin_get_team_list", description="Get the list of all teams"
    )
    async def admin_get_team_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Retrieve all teams with their players
                rows = await conn.fetch(
                    """SELECT t.team_name, p.discord_id 
                       FROM public.teams t 
                       LEFT JOIN public.players p ON t.id = p.team_id 
                       ORDER BY t.team_name"""
                )

            teams_dict = {}
            for row in rows:
                team_name = row["team_name"]
                discord_id = row["discord_id"]

                if team_name not in teams_dict:
                    teams_dict[team_name] = []

                if discord_id:
                    try:
                        user = await self.bot.fetch_user(int(discord_id))
                        teams_dict[team_name].append(user.display_name)
                    except Exception:
                        teams_dict[team_name].append(f"Unknown ({discord_id})")

            team_list = [
                f"{team}: {', '.join(players) if players else 'No players'}"
                for team, players in teams_dict.items()
            ]
            await interaction.followup.send("Teams:\n- " + "\n- ".join(team_list))
        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")

    @app_commands.command(
        name="admin_clear_all", description="(TESTING ONLY) Clear all data"
    )
    async def admin_clear_all(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Clear everything
                await conn.fetch("DELETE from public.teams")
                await conn.fetch("DELETE from public.tile_assignments")
                await conn.fetch("DELETE from public.tile_submissions")
                await conn.fetch("DELETE from public.players")

                # Clear every message in this channel, too
                await interaction.channel.purge(limit=100)
            await interaction.followup.send("All bingo data has been cleared.")
        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")

    @app_commands.command(
        name="admin_force_spawn",
        description="Force spawn a tile for easy/med/hard/elite in this channel if none exists.",
    )
    async def force_spawn(self, interaction: discord.Interaction, difficulty: str):
        difficulty_key = difficulty.strip().lower()
        category_by_difficulty = {
            "easy": 1,
            "med": 2,
            "medium": 2,
            "hard": 3,
            "elite": 4,
        }

        category = category_by_difficulty.get(difficulty_key)
        if category is None:
            await interaction.response.send_message(
                "Invalid difficulty. Use one of: easy, med, hard, elite."
            )
            return

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
                    category,
                )

                if existing_assignment:
                    await interaction.followup.send(
                        f"This team already has an active {difficulty_key} tile."
                    )
                    return

                new_assignment = await assign_random_tile(conn, team["id"], category)
                tile = await conn.fetchrow(
                    "SELECT tile_name FROM public.tiles WHERE id = $1",
                    new_assignment["tile_id"],
                )

                tile_name = tile["tile_name"] if tile else "Unknown tile"
                await interaction.followup.send(
                    f"{Emojis.THUMBS_UP} Spawned {difficulty_key} tile for {team['team_name']}: {tile_name}"
                )

        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
