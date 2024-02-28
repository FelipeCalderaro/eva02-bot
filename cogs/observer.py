from discord.ext.commands.errors import MissingPermissions
from models.member_time import (
    MemberTimeDataclass,
    member_time_dataclass_from_dict,
    member_time_dataclass_to_dict,
)
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import AppLogger
from discord.ext import commands
from os import path
import numpy as np

import discord
import json


class Observer(commands.Cog, AppLogger):
    group = discord.SlashCommandGroup(
        name="observer",
        description="Series of commands related to observing the behaviour of guild members",
    )
    my_subgroup = group.create_subgroup(
        name="my",
        description="Series of slash commands related to 'myself'(a.k.a you, the user)",
    )
    control_subgroup = group.create_subgroup(
        name="control",
        description="Commands to control the interaction with the Roles",
    )

    # List of roles
    # last equals to higher role

    member_file = "member_times.json"
    member_time_list: List[MemberTimeDataclass] = []

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.logger.info("Starting 'Observer' Cog")
        self.member_time_list = self.read_from_json()
        self.NO_PERMISSION_MSG = (
            "You dont have the right permissions to use this command!"
        )

    @my_subgroup.command(name="time")
    async def list_my_time(self, interaction: discord.Interaction) -> None:
        """Return your current total time spent connected. (Since the bot exists..)"""
        await interaction.response.defer()
        interaction.channel.typing()

        if not self.member_is_already_in_list(interaction.user.id):
            await interaction.followup.send(
                "Sorry, currently you are not registered yet in my database, check again next time that you enter in a voice channel from this guild again",
                ephemeral=True,
            )
            return None

        current_member, _ = self.get_member_from_list(interaction.user.id)

        await interaction.followup.send(
            f"According to my database you have spent a total of {current_member.total_minutes_connected / 60} hours connected to voice channels",
        )

    @my_subgroup.command(name="next_role")
    async def next_role(self, interaction: discord.Interaction) -> None:
        """Return your next role, the one that you will obtain after completing X amount of time connected"""
        await interaction.response.defer()
        interaction.channel.typing()

        role = self.get_member_highest_role(interaction.user)
        role_index = interaction.guild.roles.index(role)
        if role_index != len(interaction.guild.roles) - 1:
            next_role = interaction.guild.roles[role_index + 1]
            await interaction.followup.send(
                f"Hello {interaction.user.mention}, your next role is {next_role.mention}."
            )
        else:
            await interaction.followup.send(
                f"Hello {interaction.user.mention}, looks like you already have the highest role possible"
            )
            return

        member, _ = self.get_member_from_list(interaction.user.id)
        if (
            member is not None
            and member.expected_exponential_intervals is not None
            and len(member.expected_exponential_intervals) != 0
        ):
            minutes_left = (
                member.expected_exponential_intervals[0]
                - member.total_minutes_connected
            )
            await interaction.followup.send(
                f"You need to stay connected for another {minutes_left / 60} hours to obtain the next role",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "Sorry, I could'nt find how many hours are left. Is this your first time here?",
                ephemeral=True,
            )

    @control_subgroup.command(name="when")
    async def when_specific_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: Optional[discord.Role],
    ) -> None:
        await interaction.response.defer()
        interaction.channel.typing()

        current_member, _ = self.get_member_from_list(member.id)
        if current_member is None:
            await interaction.followup.send(
                f"User {member.mention} is not on the tracking list yet"
            )
            return

        current_role = self.get_member_highest_role(member)
        current_role_index = interaction.guild.roles.index(current_role)

        async def check_role_time(chosen_role: discord.Role):
            wanted_role_index = interaction.guild.roles.index(chosen_role)
            difference = wanted_role_index - current_role_index
            if difference < 0:
                await interaction.followup.send(
                    f"{member.mention} already have a role higher than {chosen_role.mention}"
                )
                return
            if len(current_member.expected_exponential_intervals) > difference:
                times = current_member.expected_exponential_intervals[:difference]
                self.logger.info(f"User {times=}")
                days_left = (
                    (times[-1] - current_member.total_minutes_connected) / 60
                ) / 24
                await interaction.followup.send(
                    f"The expected time for the user {member.mention} to achive {chosen_role.mention} is: {days_left} days",
                )
            else:
                await interaction.followup.send(
                    f"User {member.mention} does not have times to compare with"
                )

        if role is not None:
            await check_role_time(role)
        else:
            if current_role_index == len(interaction.guild.roles) - 1:
                await interaction.followup.send(
                    f"User {member.mention} already have the highest role possible"
                )
                return
            role = interaction.guild.roles[current_role_index + 1]
            await check_role_time(role)

    @control_subgroup.command(name="winning")
    async def get_winning_member(self, interaction: discord.Interaction):
        """Get the member with the highest time yet"""
        self.logger.info(
            f"Member {interaction.user.name} requested to know the highest member"
        )
        await interaction.response.defer()
        interaction.channel.typing()
        self.member_time_list.sort(
            key=lambda x: x.total_minutes_connected, reverse=True
        )
        current_member = self.member_time_list[0]
        member: discord.Member = interaction.guild.get_member(current_member.id)
        if member is None:
            await interaction.followup.send(
                f"Sorry, I could not find the member with the ID {current_member.id}"
            )
        else:
            await interaction.followup.send(
                f"The member with the highest time until now is {member.mention} with {current_member.total_minutes_connected/60/24} days connected"
            )

    @control_subgroup.command(name="recalculate")
    @commands.has_guild_permissions(administrator=True)
    async def recalculate_time_intervals(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        """Recalculate time intervals to gain the next roles"""
        self.logger.info(
            f"User {interaction.user.name} requested a recalculation of the intervals for member {member.name}"
        )
        try:
            await interaction.response.defer()
            interaction.channel.typing()

            current_member, i = self.get_member_from_list(member.id)
            if current_member is None:
                await interaction.followup.send(
                    f"User {member.mention} is not on the tracking list yet"
                )
                return

            current_member.expected_exponential_intervals = (
                self.calculate_exponential_interval(member)
            )
            self.member_time_list[i] = current_member
            await interaction.followup.send(
                f"Recalculated time intervals for the user {member.mention}. The new intervals are {current_member.expected_exponential_intervals} minutes"
            )
            self.save_to_json()
        except MissingPermissions:
            self.logger.error(
                f"User {interaction.user.name} don't have the correct permissions to use this command"
            )
            if not interaction.response.is_done():

                interaction.response.send_message(
                    self.NO_PERMISSION_MSG, ephemeral=True
                )
            else:
                interaction.followup.send(self.NO_PERMISSION_MSG, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error ocurred {e}")

    @control_subgroup.command(name="promote")
    @commands.has_guild_permissions(administrator=True)
    async def promote_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        """Promote a member to the next role and reset the timer tracker to the begining"""
        self.logger.info(
            f"Received promotion command for the user {member.name} by user {interaction.user.name}"
        )
        try:
            await interaction.response.defer()
            interaction.channel.typing()

            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send(
                    f"{interaction.user.mention}, you are not an administrator."
                )
                return

            m, _ = self.get_member_from_list(member.id)
            if m is None:
                await interaction.followup.send(
                    f"Current {member.mention} is not in the track list, is not possible to interact with his rank",
                    ephemeral=True,
                )
                self.logger.warning(
                    f"Despite receiving the promote command the user {member.name} is not in the lis"
                )
                return

            role = self.get_member_highest_role(member)
            role_index = interaction.guild.roles.index(role)
            if len(interaction.guild.roles) - 1 == role_index:
                await interaction.followup.send(
                    f"Current {member.mention} is already at the highest possible role.",
                    ephemeral=True,
                )
            else:
                next_role = interaction.guild.roles[role_index + 1]
                await member.remove_roles(role)
                await member.add_roles(next_role)
                await interaction.followup.send(
                    f"{member.mention} received a promotion to the role of {next_role.mention}"
                )
                current_member, i = self.get_member_from_list(member.id)
                current_member.expected_exponential_intervals = (
                    self.calculate_exponential_interval(member)
                )
                current_member.expected_exponential_intervals.pop(0)
                self.member_time_list[i] = current_member
                self.save_to_json()
        except MissingPermissions:
            self.logger.error(
                f"User {interaction.user.name} don't have the correct permissions to use this command"
            )
            if not interaction.response.is_done():
                interaction.response.send_message(
                    self.NO_PERMISSION_MSG, ephemeral=True
                )
            else:
                interaction.followup.send(self.NO_PERMISSION_MSG, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error ocurred {e}")

    @control_subgroup.command(name="demote")
    @commands.has_guild_permissions(administrator=True)
    async def demote_member(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        """Demote a member to the previous role and reset the timer tracker to the begining"""
        self.logger.info(
            f"Received demotion command for the user {member.name} by user {interaction.user.name}"
        )
        try:
            await interaction.response.defer()
            interaction.channel.typing()

            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send(
                    f"{interaction.user.mention}, you are not an administrator."
                )
                return

            m, _ = self.get_member_from_list(member.id)
            if m is None:
                await interaction.followup.send(
                    f"Current {member.mention} is not in the track list, is not possible to interact with his rank",
                    ephemeral=True,
                )
                self.logger.warning(
                    f"Despite receiving the demote command the user {member.name} is not in the lis"
                )
                return

            role = self.get_member_highest_role(member)
            role_index = interaction.guild.roles.index(role)
            if role_index - 1 > 0:
                await interaction.followup.send(
                    f"Current {member.mention} is already at the lowest possible role.",
                    ephemeral=True,
                )
            else:
                previous_role = interaction.guild.roles[role_index - 1]
                await member.remove_roles(role)
                await member.add_roles(previous_role)
                await interaction.followup.send(
                    f"{member.mention} received a demotion to the role of {previous_role.mention}"
                )
                current_member, i = self.get_member_from_list(member.id)
                current_member.expected_exponential_intervals = (
                    self.calculate_exponential_interval(member)
                )
                current_member.expected_exponential_intervals.pop(0)
                self.member_time_list[i] = current_member
                self.save_to_json()
        except MissingPermissions:
            self.logger.error(
                f"User {interaction.user.name} don't have the correct permissions to use this command"
            )
            if not interaction.response.is_done():
                interaction.response.send_message(
                    self.NO_PERMISSION_MSG, ephemeral=True
                )
            else:
                interaction.followup.send(self.NO_PERMISSION_MSG, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error ocurred {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Checks if the user joined the channels"""
        self.logger.info(
            f"Voice state update event received: {member.name} - {member.id}"
        )
        if member.bot:
            return None
        if before.channel is None and after.channel is not None:
            # User connected to voice channel
            await self.user_joined_voice_channel(member)
        elif before.channel is not None and after.channel is None:
            # User disconnected from voice channel
            await self.user_left_voice_channel(member)
        else:
            self.logger.debug(f"User {member.name} changed status, but still connected")

    async def user_joined_voice_channel(self, member: discord.Member) -> None:
        self.logger.info(
            f"User {member.name} joined the voice channel, saving the connection time"
        )
        if not self.member_is_already_in_list(member.id):
            self.logger.info("User not recorded yet, creating entry")
            self.member_time_list.append(
                MemberTimeDataclass(
                    id=member.id,
                    name=member.name,
                    highest_role_id=self.get_member_highest_role(member).id,
                    connected_at=datetime.now(),
                    last_connected_at=datetime.now(),
                    expected_exponential_intervals=self.calculate_exponential_interval(
                        member
                    ),
                )
            )
        else:
            self.logger.info("User found in the record, updating entry")
            current_member, i = self.get_member_from_list(member.id)
            self.logger.info(
                f"Last connection was on {current_member.last_connected_at}"
            )
            current_member.last_connected_at = current_member.connected_at
            current_member.connected_at = datetime.now()

            highest_role = self.get_member_highest_role(member)
            current_member.highest_role_id = highest_role.id

            if current_member.expected_exponential_intervals is None:
                current_member.expected_exponential_intervals = (
                    self.calculate_exponential_interval(member)
                )

            if len(current_member.expected_exponential_intervals) == 0:
                return None
            elif (
                current_member.total_minutes_connected
                > current_member.expected_exponential_intervals[0]
            ):
                intervals_completed = [
                    interval
                    for interval in current_member.expected_exponential_intervals
                    if current_member.total_minutes_connected > interval
                ]
                self.logger.info(
                    f"Current user {member.name} has meet {len(intervals_completed)}({intervals_completed=}) required interval(s), upgrading his roles"
                )
                # Remove current intervals already complete
                for i in range(len(intervals_completed)):
                    current_member.expected_exponential_intervals.pop(0)

                role_index = member.guild.roles.index(highest_role)
                current_role = member.guild.roles[role_index]
                role_above = member.guild.roles[role_index:][len(intervals_completed)]

                await member.remove_roles(
                    current_role,
                    reason="Spent the required amount, promotion given",
                )
                await member.add_roles(
                    role_above,
                    reason="Spent the required amount, promotion given",
                )

                if member.can_send():
                    await member.send(
                        f"Hello, you are now elegible to the role of `{role_above.name}`. Congratulations!"
                    )
            else:
                self.logger.info(
                    f"Current user {member.name}({member.id}) has not meet the required time yet to unlock the next role"
                )
            self.member_time_list[i] = current_member

        self.save_to_json()

    async def user_left_voice_channel(self, member: discord.Member) -> None:
        self.logger.info(
            f"User {member.name} left the voice channel, saving the disconnection time"
        )
        current_member, i = self.get_member_from_list(member.id)
        if current_member is None or i is None:
            return None

        current_member.disconnected_at = datetime.now()
        current_member.update_last_connected_by()
        current_member.update_total_minutes()
        self.member_time_list[i] = current_member
        self.save_to_json()

    def member_is_already_in_list(self, id: int) -> bool:
        return id in [member.id for member in self.member_time_list]

    def get_member_highest_role(self, member: discord.Member):
        highest_role = member.roles[-1]
        if highest_role.name == member.name:
            highest_role = member.roles[-2]
        return highest_role

    def get_member_from_list(
        self,
        id: int,
    ) -> Tuple[MemberTimeDataclass, int] | Tuple[None, None]:
        if not self.member_is_already_in_list(id):
            return None, None

        m = [member_obs for member_obs in self.member_time_list if member_obs.id == id]
        if len(m) == 0:
            return None, None

        current_member = m[-1]
        m.clear()
        del m

        return current_member, self.member_time_list.index(current_member)

    def calculate_exponential_interval(self, member: discord.Member):
        self.logger.info(f"Calculating exponential interval for {member.display_name}")
        starting_minutes_required = 200 * 60  # Hours * min = Total Min
        # 2 years * days * hours * minutes = Total in minutes
        total_minutes_to_max_role = 2 * 365 * 24 * 60

        roles = member.guild.roles
        # Split roles based on the current member role
        current_role = self.get_member_highest_role(member)
        index = roles.index(current_role)
        roles = roles[index:]

        intervals = np.geomspace(
            starting_minutes_required,
            total_minutes_to_max_role,
            len(roles),
        )
        intervals_list = intervals.tolist()

        return intervals_list

    def save_to_json(self):
        self.logger.debug(f"[{self.__class__.__name__}] Opening json file to save")
        with open(self.member_file, "w") as f:
            self.logger.debug(f"[{self.__class__.__name__}] Json Record file open")
            json.dump(
                member_time_dataclass_to_dict(self.member_time_list),
                fp=f,
                indent=4,
            )
        self.logger.debug(f"[{self.__class__.__name__}] Operation finished. File saved")

    def read_from_json(self):
        if not path.exists(self.member_file):
            return []
        with open(self.member_file, "r") as f:
            parsed_data = json.load(f)
            return member_time_dataclass_from_dict(parsed_data)
