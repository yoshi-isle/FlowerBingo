from discord.ext import commands
from rapidfuzz import fuzz
import string

MATCH_THRESHOLD = 85


class CustomerServiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Clean and split message
        clean_text = message.content.lower().translate(
            str.maketrans("", "", string.punctuation)
        )
        words = clean_text.split()

        if self.needs_help_viewing_board(words):
            await message.channel.send(
                f"Hi {message.author.mention}, I can help. To view your bingo board, just use the `/view_board` command in your team channel!"
            )

    def needs_help_viewing_board(self, words):
        verb_query = ["view", "see", "how", "what command"]
        action_query = ["board", "tile"]

        has_verb = False
        has_action = False

        for query in verb_query:
            if not has_verb:
                has_verb = self.fuzzy_contains(words, query)
        for query in action_query:
            if not has_action:
                has_action = self.fuzzy_contains(words, query)

        return has_verb and has_action

    def fuzzy_contains(self, words, target):
        """
        # Fuzzy match with threshold
        """
        print(target, words)
        return any(fuzz.ratio(word, target) >= MATCH_THRESHOLD for word in words)


async def setup(bot):
    await bot.add_cog(CustomerServiceCog(bot))
