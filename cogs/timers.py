from datetime import datetime, timezone

from discord import Embed
from discord.ext import commands, tasks
from utils.get_board_payload import get_board_payload
from utils.get_global_state import get_global_state

class TimersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_flower_basket_expiration.start()

    @tasks.loop(minutes=1)
    async def check_flower_basket_expiration(self):
        try:
            state = await get_global_state(self.bot.db_pool)
            expires = state["flower_basket_expires"]
            if not expires:
                return
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:

                all_teams = await self.bot.db_pool.fetch(
                    "SELECT id, discord_channel_id, team_name FROM public.teams WHERE discord_channel_id IS NOT NULL"
                )

                for team in all_teams:
                    
                    # Remove flower basket from global config AND tile assignments worldwide
                    await self.bot.db_pool.fetch(
                        """
                        UPDATE public.tile_assignments 
                        SET is_active=false, was_skipped=true
                        WHERE category=5 AND team_id=$1
                        """, # Was skipped = just dont count it for 999 points. maybe improve
                        team["id"],
                    )

                    # Update the first row from global_config
                    await self.bot.db_pool.fetch(
                        """
                        UPDATE public.global_game_states
                        SET is_flower_basket_active=false, flower_basket_expires=null
                        WHERE id=0
                        """
                    )

                    team_channel = self.bot.get_channel(int(team["discord_channel_id"]))
                    if team_channel is None:
                        try:
                            team_channel = await self.bot.fetch_channel(
                                int(team["discord_channel_id"])
                            )
                        except Exception:
                            continue

                    if not team_channel:
                        continue

                    await team_channel.send(embed=Embed(description="🕐The flower basket event has expired."))
                    team_embed, file = await get_board_payload(
                        self.bot.db_pool,
                        team_id=team["id"],
                        team=team # I really dont know anymore lmfao
                    )
                    if team_embed and file:
                        await team_channel.send(embed=team_embed, file=file)
        except Exception as e:
            print(f"Error in check_flower_basket_expiration: {e}")

    @check_flower_basket_expiration.before_loop
    async def before_check_flower_basket_expiration(self):
        await self.bot.wait_until_ready()

   

async def setup(bot):
    await bot.add_cog(TimersCog(bot))
