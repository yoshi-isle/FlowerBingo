from discord.ext import commands
from rapidfuzz import fuzz
import string

MATCH_THRESHOLD = 60


class CustomerServiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        clean_text = message.content.lower().translate(
            str.maketrans("", "", string.punctuation)
        )

        if fuzz.ratio(clean_text, "how do i view board") >= 75:
            await message.channel.send(
                f"Hey {message.author.mention}👋. To view your board, use `/board` in your team channel."
            )

        elif fuzz.ratio(clean_text, "how do i check the board") >= 75:
            await message.channel.send(
                f"Hey {message.author.mention} 👋. To view your board, use `/board` in your team channel."
            )

        elif fuzz.ratio(clean_text, "how check what tile we're on") >= 75:
            await message.channel.send(
                f"Hey {message.author.mention} 👋. To view your board, use `/board` in your team channel."
            )


async def setup(bot):
    await bot.add_cog(CustomerServiceCog(bot))
