from discord.ext import commands
import os
from constants import Emojis


class ApprovalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if str(payload.emoji) not in [
            Emojis.THUMBS_UP,
            Emojis.NO,
            Emojis.FORCE,
            Emojis.EXPLAIN,
            Emojis.HIGHSCORES,
        ]:
            return

        if str(payload.channel_id) != str(os.getenv("PENDING_SUBMISSIONS_CHANNEL_ID")):
            return

        print(payload.emoji)

        if payload.emoji.name == "white_check_mark":  # or use payload.emoji directly
            print("white check mark?")
            pass

        if payload.emoji.name == "white_check_mark":  # or use payload.emoji directly
            print("white check mark?")
            pass

    async def handle_approval():
        pass


async def setup(bot):
    await bot.add_cog(ApprovalCog(bot))
