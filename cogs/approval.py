import datetime

import discord
from discord.ext import commands
import os
import asyncio
import random
from constants import Emojis
from utils.register_team import assign_random_tile
from utils.get_board_payload import get_board_payload
import time


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
        ]
        self.reaction_cooldown_seconds = 6
        self.last_reaction_by_user = {}
        self.users_in_progress = set()
        self.cooldown_lock = asyncio.Lock()

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

        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return

        async with self.cooldown_lock:
            if payload.user_id in self.users_in_progress:
                await channel.send(
                    "You're already processing a submission. Please wait for it to finish.",
                    delete_after=3,
                )
                return

            last_reaction_at = self.last_reaction_by_user.get(payload.user_id)
            if last_reaction_at is not None:
                elapsed = time.monotonic() - last_reaction_at
                if elapsed < self.reaction_cooldown_seconds:
                    remaining = int(self.reaction_cooldown_seconds - elapsed)
                    await channel.send(
                        f"On cooldown: please wait {remaining}s and try again <@{payload.user_id}>.",
                        delete_after=max(remaining, 1),
                    )
                    return

            self.users_in_progress.add(payload.user_id)
            self.last_reaction_by_user[payload.user_id] = time.monotonic()

        try:
            if str(payload.emoji) == Emojis.THUMBS_UP:
                await self._handle_reaction(payload)
            elif str(payload.emoji) == Emojis.NO:
                await self._handle_reaction(payload, is_approved=False)
            elif str(payload.emoji) == Emojis.FORCE:
                await self._handle_reaction(payload, force_complete=True)
        finally:
            async with self.cooldown_lock:
                self.users_in_progress.discard(payload.user_id)

    async def _handle_reaction(self, payload, is_approved=True, force_complete=False):
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

        updated_tile_assignment = None
        if is_approved:
            updated_tile_assignment = await self._update_tile_assignment(
                tile_submission_updated, force_complete
            )

            # Note: The new tile generation has already happened at this point. This is solely for UX
            if updated_tile_assignment["remaining_submissions"] <= 0:
                await team_channel.send(embed=discord.Embed(description=f"**Tile** complete! {Emojis.THUMBS_UP} Posting your new board..."))
                # Unpin all previous messages
                async for msg in team_channel.history(limit=100):
                    if msg.pinned:
                        try:
                            await msg.unpin()
                        except Exception:
                            pass
                team_embed, file = await get_board_payload(
                    self.bot.db_pool,
                    team["id"],
                    team=team,
                    new_tile_index=updated_tile_assignment["category"],
                )
                if team_embed and file:
                    board_msg = await team_channel.send(embed=team_embed, file=file)
                    try:
                        await board_msg.pin()
                    except Exception:
                        pass
            else:
                await team_channel.send(embed=discord.Embed(description=f"Your team made progress on the tile. You still need {updated_tile_assignment['remaining_submissions']}."))
                

        await self._update_admin_message(
            admin_message, is_approved, payload.member.display_name, updated_tile_assignment
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

    async def _update_tile_assignment(self, tile_submission, force_complete=False):
        """
        Update the tile assignment from the submission.

        Returns the remaining submissions left for the assignment
        """
        tile_assignment = await self.bot.db_pool.fetchrow(
            "SELECT * FROM public.tile_assignments WHERE id = $1",
            tile_submission["tile_assignment_id"],
        )

        if force_complete:
            updated_tile_assignment = await self.bot.db_pool.fetchrow(
                "UPDATE public.tile_assignments SET remaining_submissions = 0 WHERE id = $1 RETURNING *",
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

                # If they completed a flower basket
                if updated_tile_assignment["category"] == 5:
                    all_teams = await self.bot.db_pool.fetch(
                    "SELECT id, discord_channel_id, team_name FROM public.teams WHERE discord_channel_id IS NOT NULL"
                )

                    for team in all_teams:
                        # Remove flower basket from global config AND tile assignments worldwide
                        award_points = team["id"] != updated_tile_assignment["team_id"]
                        await self.bot.db_pool.fetch(
                            """
                            UPDATE public.tile_assignments 
                            SET is_active=false, was_skipped=$1
                            WHERE category=5 AND team_id=$2
                            """,
                            award_points,
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

                        if award_points:
                            await team_channel.send(embed=discord.Embed(description="Another team completed the flower basket."))
                            # Unpin all previous messages
                            async for msg in team_channel.history(limit=100):
                                if msg.pinned:
                                    try:
                                        await msg.unpin()
                                    except Exception:
                                        pass
                            team_embed, file = await get_board_payload(
                                self.bot.db_pool,
                                team_id=team["id"],
                                team=team
                            )
                            if team_embed and file:
                                board_msg = await team_channel.send(embed=team_embed, file=file)
                                try:
                                    await board_msg.pin()
                                except Exception:
                                    pass
                else:
                    await self._roll_basket_chance(tile_assignment["category"], skip_team_id=tile_assignment["team_id"])

                    # Generate a new tile
                    await assign_random_tile(
                        self.bot.db_pool,
                        tile_assignment["team_id"],
                        tile_assignment["category"],
                    )

            return updated_tile_assignment

        return 0

    async def _roll_basket_chance(self, category: int, skip_team_id=None):
        config_names_by_category = {
            1: "basket_chance_easy",
            2: "basket_chance_medium",
            3: "basket_chance_hard",
            4: "basket_chance_elite",
        }

        config_name = config_names_by_category.get(category)
        if not config_name:
            return

        amount = await self.bot.db_pool.fetchval(
            "SELECT amount FROM public.global_configs WHERE name = $1",
            config_name,
        )

        if not amount or amount <= 0:
            return

        if random.randint(1, int(amount)) == 1:
            await self._spawn_flower_basket(skip_team_id=skip_team_id)

    async def _spawn_flower_basket(self, skip_team_id=None):
        did_spawn = False
        try:
            async with self.bot.db_pool.acquire() as conn:
                async with conn.transaction():
                    game_state = await conn.fetchrow(
                        """
                        SELECT *
                        FROM public.global_game_states
                        ORDER BY id ASC
                        LIMIT 1
                        FOR UPDATE
                        """
                    )

                    if not game_state:
                        return False

                    if game_state["is_flower_basket_active"]:
                        # You have a funny feeling like you would have spawned a flower basket...
                        all_teams = await self.bot.db_pool.fetch(
                            "SELECT id, discord_channel_id, team_name FROM public.teams WHERE discord_channel_id IS NOT NULL"
                        )

                        for team in all_teams:
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

                            await team_channel.send(embed=discord.Embed(description="❗You have a funny feeling like a flower basket would have spawned.", color=discord.Color.red()))
                        return False

                    flower_basket_tile = await conn.fetchrow(
                        """
                        SELECT *
                        FROM public.tiles
                        WHERE category = 5
                            AND id NOT IN (
                                SELECT tile_id FROM public.flower_basket_history
                            )
                        ORDER BY RANDOM()
                        LIMIT 1
                        """
                    )

                    if not flower_basket_tile:
                        return False

                    await conn.fetchrow(
                        """
                        UPDATE public.global_game_states
                        SET is_flower_basket_active = true,
                            flower_basket_expires = $1
                        WHERE id = (
                            SELECT id FROM public.global_game_states
                            ORDER BY id ASC
                            LIMIT 1
                        )
                        """,
                        datetime.datetime.fromtimestamp(time.time() + 86400),
                    )

                    await conn.fetchrow(
                        """
                        INSERT INTO public.flower_basket_history (tile_id)
                        SELECT $1
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM public.flower_basket_history
                            WHERE tile_id = $1
                        )
                        """,
                        flower_basket_tile["id"],
                    )

                    did_spawn = True

            if not did_spawn:
                return False

            all_teams = await self.bot.db_pool.fetch(
                "SELECT id, discord_channel_id, team_name FROM public.teams WHERE discord_channel_id IS NOT NULL"
            )

            for team in all_teams:
                
                # Insert the flower basket into their tile assignment.
                await self.bot.db_pool.fetch(
                    """
                    INSERT INTO public.tile_assignments 
                    (team_id, tile_id, is_active, category, remaining_submissions, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    """,
                    team["id"],
                    flower_basket_tile["id"],
                    True,
                    5,
                    flower_basket_tile["completion_counter"],
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

                await team_channel.send(embed=discord.Embed(description="🌸 A flower basket has spawned!"))

                if skip_team_id is not None and team["id"] == skip_team_id:
                    continue

                team_embed, file = await get_board_payload(
                    self.bot.db_pool,
                    team["id"],
                    team=team,
                )
                if team_embed and file:
                    await team_channel.send(embed=team_embed, file=file)
        except Exception as e:
            print(e)
            return False
        return did_spawn

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
        self, admin_message: discord.Message, is_approved: bool, approver_name: str, updated_tile_assignment
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
        
        if updated_tile_assignment:
            admin_embed.set_footer(text=f"Submission ID: {updated_tile_assignment['id']}")
        else:
            admin_embed.set_footer(text="")

        receipt_channel = self.approved_channel if is_approved else self.denied_channel
        # await receipt_channel.send(admin_embed.image.url)
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
