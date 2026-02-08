import discord
from discord import app_commands
from discord.ext import commands


class HelloCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello!")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Hello, {interaction.user.mention}! 👋"
        )

    @app_commands.command(name="dbtest", description="Test database connection")
    async def dbtest(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            # Acquire connection from pool
            async with self.bot.db_pool.acquire() as conn:
                # Get all players
                result = await conn.fetch("SELECT * FROM public.players")
            # Connection automatically released back to pool

            # Format and send result
            if result:
                # Show count
                count = len(result)
                result_text = f"Found {count} player(s):\n\n"

                # Format each row
                for row in result:
                    row_dict = dict(row)
                    result_text += "\n".join(
                        [f"{key}: {value}" for key, value in row_dict.items()]
                    )
                    result_text += "\n" + "-" * 40 + "\n"

                await interaction.followup.send(f"```\n{result_text}\n```")
            else:
                await interaction.followup.send("No players found in database.")

        except Exception as e:
            await interaction.followup.send(f"Database error: {str(e)}")


async def setup(bot):
    await bot.add_cog(HelloCog(bot))
