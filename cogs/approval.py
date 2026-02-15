import discord
from discord.ext import commands
import os
from constants import Emojis
from utils.register_team import assign_random_tile
from utils.get_board_payload import get_board_payload


class ApprovalCog(commands.Cog):
    """
    ApprovalCog

    Handles the operation of reacting to a submission with the given reactions.
    Performs tasks based on the reaction given.
    """

    def __init__(self, bot):
        self.bot = bot
        self.pending_channel_id = int(os.getenv("PENDING_SUBMISSIONS_CHANNEL_ID"))
        self.approved_channel_id = int(os.getenv("APPROVED_SUBMISSIONS_CHANNEL_ID"))
        self.denied_channel_id = int(os.getenv("DENIED_SUBMISSIONS_CHANNEL_ID"))
        self.accepted_reactions = [
            Emojis.THUMBS_UP,
            Emojis.NO,
            Emojis.FORCE,
            Emojis.EXPLAIN,
        ]

    @property
    def pending_channel(self):
        return self.bot.get_channel(self.pending_channel_id)

    @property
    def approved_channel(self):
        return self.bot.get_channel(self.approved_channel_id)

    @property
    def denied_channel(self):
        return self.bot.get_channel(self.denied_channel_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.channel_id != self.pending_channel.id:
            return

        if str(payload.emoji) not in self.accepted_reactions:
            return

        if str(payload.emoji) == Emojis.THUMBS_UP:
            await self._handle_reaction(payload, is_approved=True)

        if str(payload.emoji) == Emojis.NO:
            await self._handle_reaction(payload, is_approved=False)

        if str(payload.emoji) == Emojis.FORCE:
            print("Forcing completion")
        if str(payload.emoji) == Emojis.EXPLAIN:
            print("Explaining")

    async def _handle_reaction(self, payload, is_approved=True):
        admin_message = await self._fetch_admin_message(payload)

        if await self._submission_already_approved(payload.message_id):
            await admin_message.reply(
                "⚠️ This submission seems to already be approved, and can be safely deleted.",
                delete_after=3,
            )
            return

        if await self._old_submission_already_advanced(payload.message_id):
            await admin_message.reply(
                "⚠️ Looks like they're already done with this tile. This is an old submission and can be safely deleted.\n",
                delete_after=3,
            )
            return

        tile_submission_updated = await self._update_submission_status(
            payload.message_id, is_approved
        )

        team = await self._get_team_for_submission(tile_submission_updated)
        team_channel = self.bot.get_channel(int(team["discord_channel_id"]))

        if is_approved:
            remaining_submissions = await self._update_tile_assignment(
                tile_submission_updated
            )

            # Note: The new tile generation has already happened at this point. This is solely for UX
            if remaining_submissions <= 0:
                await team_channel.send(
                    f"**Tile** complete! {Emojis.THUMBS_UP} Posting your new board..."
                )
                team_embed, file = await get_board_payload(
                    self.bot.db_pool,
                    team["id"],
                    team=team,
                )
                if team_embed and file:
                    await team_channel.send(embed=team_embed, file=file)
            else:
                await team_channel.send(
                    f"Your team made progress on the tile. You still need {remaining_submissions}."
                )

        await self._update_admin_message(
            admin_message, is_approved, payload.member.display_name
        )

        # Get player message embed
        player_message: discord.Message = await team_channel.fetch_message(
            tile_submission_updated["receipt_message_id"]
        )

        await self._update_player_message(
            player_message, is_approved, payload.member.display_name
        )

        await admin_message.delete()

    async def _fetch_admin_message(self, payload) -> discord.Message:
        channel = self.bot.get_channel(payload.channel_id)
        return await channel.fetch_message(payload.message_id)

    async def _submission_already_approved(self, message_id) -> bool:
        already_approved = await self.bot.db_pool.fetchrow(
            "SELECT * from public.tile_submissions WHERE is_approved = true AND admin_receipt_message_id = $1",
            str(message_id),
        )
        return bool(already_approved)

    async def _old_submission_already_advanced(self, message_id) -> bool:
        old_submission = await self.bot.db_pool.fetchrow(
            "SELECT ts.*, ta.remaining_submissions FROM public.tile_submissions ts JOIN public.tile_assignments ta ON ts.tile_assignment_id = ta.id WHERE ts.admin_receipt_message_id = $1 AND ta.is_active = false",
            str(message_id),
        )
        if old_submission and old_submission["remaining_submissions"] <= 0:
            return True
        return False

    async def _update_submission_status(self, message_id, is_approved):
        return await self.bot.db_pool.fetchrow(
            "UPDATE public.tile_submissions SET is_approved = $1, updated_at = NOW() WHERE admin_receipt_message_id = $2 RETURNING *",
            is_approved,
            str(message_id),
        )

    async def _update_tile_assignment(self, tile_submission):
        """
        Update the tile assignment from the submission.

        Returns the remaining submissions left for the assignment
        """
        tile_assignment = await self.bot.db_pool.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE id = $1",
            tile_submission["tile_assignment_id"],
        )

        if tile_assignment["remaining_submissions"] > 0:
            updated_tile_assignment = await self.bot.db_pool.fetchrow(
                "UPDATE public.tile_assignments SET remaining_submissions = remaining_submissions - 1 WHERE id = $1 RETURNING *",
                tile_submission["tile_assignment_id"],
            )

            if updated_tile_assignment["remaining_submissions"] <= 0:
                await self.bot.db_pool.execute(
                    "UPDATE public.tile_assignments SET is_active = false WHERE id = $1",
                    tile_submission["tile_assignment_id"],
                )

                # Generate a new tile
                await assign_random_tile(
                    self.bot.db_pool,
                    tile_assignment["team_id"],
                    tile_assignment["category"],
                )

            return updated_tile_assignment["remaining_submissions"]

        return 0

    async def _get_team_for_submission(self, tile_submission_updated):
        tile_assignment = await self.bot.db_pool.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE id = $1",
            tile_submission_updated["tile_assignment_id"],
        )
        return await self.bot.db_pool.fetchrow(
            "SELECT * FROM public.teams WHERE id = $1",
            tile_assignment["team_id"],
        )

    async def _update_admin_message(
        self, admin_message: discord.Message, is_approved: bool, approver_name: str
    ):
        admin_embed = admin_message.embeds[0].copy()
        admin_embed.color = (
            discord.Color.green() if is_approved else discord.Color.red()
        )
        admin_embed.set_field_at(
            0,
            name=f"{Emojis.THUMBS_UP if is_approved else '❌'} {'Approved' if is_approved else 'Denied'} by {approver_name}",
            value="",
            inline=False,
        )
        # Remove field 3 (instructions)
        admin_embed.remove_field(3)
        admin_embed.remove_footer()

        receipt_channel = self.approved_channel if is_approved else self.denied_channel
        await receipt_channel.send(embed=admin_embed)

    async def _update_player_message(
        self, player_message: discord.Message, is_approved: bool, approver_name: str
    ):
        player_embed = player_message.embeds[0].copy()
        player_embed.color = (
            discord.Color.green() if is_approved else discord.Color.red()
        )
        player_embed.set_field_at(
            0,
            name=f"{Emojis.THUMBS_UP if is_approved else '❌'} {'Approved' if is_approved else 'Denied'} by {approver_name}",
            value="",
            inline=False,
        )
        player_embed.remove_field(1)
        player_embed.remove_footer()
        await player_message.edit(embed=player_embed)


async def setup(bot):
    await bot.add_cog(ApprovalCog(bot))
