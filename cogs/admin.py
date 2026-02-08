import discord
from discord import app_commands
from discord.ext import commands


from utils.register_team import register_team


class ConfirmView(discord.ui.View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="Action cancelled.", view=None)


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="admin_make_team", description="Register a new team")
    async def admin_make_team(self, interaction: discord.Interaction, team_name: str):
        # Show confirmation dialog
        view = ConfirmView()
        await interaction.response.send_message(
            f"Are you sure you want to create team '{team_name}'?",
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if not view.value:
            return

        try:
            async with self.bot.db_pool.acquire() as conn:
                team_id = await register_team(conn, team_name)

            await interaction.followup.send(
                f"Team '{team_name}' (ID: {team_id}) has been registered with 4 random tiles by {interaction.user.mention}."
            )
        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")

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
        # Show confirmation dialog
        view = ConfirmView()
        await interaction.response.send_message(
            f"Are you sure you want to register {player.mention} to team '{team_name}'?",
            view=view,
            ephemeral=True,
        )
        await view.wait()

        if not view.value:
            return

        try:
            async with self.bot.db_pool.acquire() as conn:
                # Get team_id from team_name
                team_row = await conn.fetchrow(
                    "SELECT id FROM public.teams WHERE team_name = $1", team_name
                )

                if not team_row:
                    await interaction.followup.send(f"Team '{team_name}' not found.")
                    return

                team_id = team_row["id"]

                # Insert player into database
                await conn.execute(
                    "INSERT INTO public.players (discord_id, team_id) VALUES ($1, $2)",
                    str(player.id),
                    team_id,
                )

            await interaction.followup.send(
                f"Player {player.mention} has been registered to team '{team_name}'."
            )
        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")

    @app_commands.command(
        name="admin_get_team_list", description="Get the list of all teams"
    )
    async def admin_get_team_list(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.bot.db_pool.acquire() as conn:
                # Retrieve all teams from database
                rows = await conn.fetch("SELECT team_name FROM public.teams")
                team_list = [row["team_name"] for row in rows]
            await interaction.followup.send(f"Teams:\n- {', \n- '.join(team_list)}")
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


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
