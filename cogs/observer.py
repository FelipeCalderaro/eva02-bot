from models.member_time import (
    MemberTimeDataclass,
    member_time_dataclass_from_dict,
    member_time_dataclass_to_dict,
)
from datetime import datetime, timedelta
from utils.logger import AppLogger
from discord.ext import commands
from typing import List, Tuple
from pprint import pprint
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

    # List of roles
    # last equals to higher role

    member_file = "member_times.json"
    member_time_list: List[MemberTimeDataclass] = []

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.logger.info("Starting 'Observer' Cog")
        self.member_time_list = self.read_from_json()

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

    def update_user_role(self):
        """Update user role base in the time"""
        ...

    def calculate_exponential_interval(self, member: discord.Member):
        self.logger.info(f"Calculating exponential interval for {member.display_name}")
        starting_minutes_required = 200 * 60  # Hours * min = Total Min
        roles = member.guild.roles
        # Split roles based on the current member role
        current_role = self.get_member_highest_role(member)
        index = roles.index(current_role)
        roles = roles[index:]

        intervals = np.geomspace(1, 100, len(roles))
        # Aplicar o aumento exponencial
        for i in range(1, len(intervals)):
            intervals[i] = intervals[i - 1] + starting_minutes_required
        intervals_list = intervals.tolist()
        intervals_list.pop(0)  # first is always 1.0, so we remove it

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
