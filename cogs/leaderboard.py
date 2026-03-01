import os
from datetime import timedelta
import discord
from discord.ext import commands, tasks

from constants import Emojis
from utils.get_leaderboard import get_leaderboard

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.leaderboard_channel_id = int(os.getenv("LEADERBOARD_CHANNEL_ID", "0"))
        self.leaderboard_message_id = None
        self.update_leaderboard_embed.start()

    async def cog_unload(self):
        self.update_leaderboard_embed.cancel()

    async def _build_embed(self, leaderboard) -> discord.Embed:
        next_update_dt = discord.utils.utcnow() + timedelta(minutes=2)
        next_update_ts = int(next_update_dt.timestamp())
        footer_text = ""

        embed = discord.Embed(
            title=f"{Emojis.HIGHSCORES} Leaderboard",
            color=discord.Color.gold(),
        )

        if not leaderboard:
            embed.description = "No teams found yet."
            embed.set_footer(text=footer_text)
            return embed

        top_teams = leaderboard
        lines = []
        medals = [":first_place_medal:", ":second_place_medal:", ":third_place_medal:"]
        prev_points = None
        rank = 0
        display_rank = 0
        for team in top_teams:
            team_name = team["team_name"]
            points = team["points"]
            # Handle ties: same rank for same points
            if points != prev_points:
                rank += 1
                display_rank = rank
            # Medal for top 3
            if display_rank <= 3:
                medal = medals[display_rank - 1]
                rank_str = medal
            else:
                rank_str = f"#{display_rank}"
            lines.append(f"**{rank_str}** {team_name} — **{points} pts**")
            prev_points = points

        embed.description = "\n".join(lines)
        embed.add_field(name="", value=f"Next Update: <t:{next_update_ts}:R>", inline=False)
        embed.set_footer(text=footer_text)
        return embed

    async def _record_point_history(self, conn, leaderboard):
        if not leaderboard:
            return

        snapshot_datetime = discord.utils.utcnow().replace(tzinfo=None)
        rows = [
            (snapshot_datetime, team["team_id"], team["points"])
            for team in leaderboard
        ]

        try:
            await conn.executemany(
                """
                INSERT INTO public.point_history (date, team_id, points)
                VALUES ($1, $2, $3)
                """,
                rows,
            )
        except Exception as e:
            print(f"Error recording point history: {e}")

    async def _get_or_create_message(
        self, channel: discord.TextChannel
    ) -> discord.Message | None:
        if self.leaderboard_message_id:
            try:
                return await channel.fetch_message(self.leaderboard_message_id)
            except discord.NotFound:
                self.leaderboard_message_id = None

        async for message in channel.history(limit=50):
            if (
                message.author.id == self.bot.user.id
                and message.embeds
                and message.embeds[0].title
                and "Leaderboard" in message.embeds[0].title
            ):
                self.leaderboard_message_id = message.id
                return message

        return None

    @tasks.loop(minutes=5)
    async def update_leaderboard_embed(self):
        if not self.leaderboard_channel_id:
            return

        channel = self.bot.get_channel(self.leaderboard_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(self.leaderboard_channel_id)
            except Exception:
                return

        if not isinstance(channel, discord.TextChannel):
            return

        async with self.bot.db_pool.acquire() as conn:
            leaderboard, _, _ = await get_leaderboard(conn)
            await self._record_point_history(conn, leaderboard)

        embed = await self._build_embed(leaderboard)
        leaderboard_message = await self._get_or_create_message(channel)

        if leaderboard_message:
            await leaderboard_message.edit(embed=embed)
        else:
            new_message = await channel.send(embed=embed)
            self.leaderboard_message_id = new_message.id

    @update_leaderboard_embed.before_loop
    async def before_update_leaderboard_embed(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
