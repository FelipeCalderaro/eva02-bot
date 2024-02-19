import re
from discord.commands.context import ApplicationContext
from typing import List, Optional
from discord.ext import commands
from datetime import datetime

from time import sleep
import threading
import discord
import pathlib
import asyncio
import select
import socket
import io


from utils.logger import AppLogger
from configparser import ConfigParser

CONFIG = ConfigParser()
CONFIG.read("config.ini")


INTEREST_GAMES_CHANNEL = CONFIG["GUILDS"]["ChannelsOfInteress"]
FORUM_CHANNEL = CONFIG["GUILDS"]["ForumChannels"]


class Eva(commands.Cog, AppLogger):
    def __init__(self, bot: discord.bot.Bot) -> None:
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"{self.__class__.__name__} ready!")
        activity = discord.Game(
            name="while waiting pilot",
            # large_image_url="https://cdn.vox-cdn.com/thumbor/c5zbWv2FxMLKWZzV0AsGtIAR7xY=/1400x1400/filters:format(jpeg)/cdn.vox-cdn.com/uploads/chorus_asset/file/19577071/op_39__1_.jpg",
            # large_image_text="EVA01 Ready",
        )
        await self.bot.change_presence(status=discord.Status.online, activity=activity)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        self.logger.info(
            f"New message received from: {message.author.name} ({message.author.display_name})"
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        self.logger.info(f"Channel update event received: {before} {after}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        ...
        # self.logger.info(
        #     f"Voice state update event received: {member}, {before} {after}"
        # )

    @commands.slash_command()
    async def ping(
        self,
        ctx: ApplicationContext,
    ):
        """Give back a pong with latency response"""
        await ctx.respond(f"Pong! Latency is {self.bot.latency}")

    # async def parse_steam_channel(self, message: discord.Message):
    #     if len(urls) == 0 and "steam" not in urls[0]:
    #         return
    #     steam = SteamScrapper()
    #     urls = steam.filter_url(message.content)
    #     async with message.channel.typing():
    #         await message.reply(f"{urls[0].split('/')[-2].replace('_',' ')} の入力の作成")
    #     categories = steam.find_game_category(urls[0])
    #     categories[-1] = categories[-1].replace("\t", "")
    #     forum = self.bot.get_channel(FORUM_CHANNEL)
    #     if isinstance(forum, discord.ForumChannel):
    #         tag_names = set([tag.name for tag in forum.available_tags])
    #         new_tags = list(tag_names.difference(set(categories)))
    #         if len(new_tags) != 0:
    #             for tag in new_tags:
    #                 try:
    #                     await forum.create_tag(name=tag[:19])
    #                 except Exception:
    #                     continue
    #         await forum.create_thread(
    #             name=urls[0].split("/")[-2].replace("_", " "),
    #             content=f"{urls[0]}\nによって追加: {message.author.mention}",
    #             applied_tags=[
    #                 tag
    #                 for tag in list(
    #                     filter(
    #                         lambda x: x.name in categories,
    #                         forum.available_tags,
    #                     )
    #                 )
    #             ][:4],
    #         )
    #     await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        self.logger.debug(
            f"Message sent in the chats from {message.author.name}: {message.content}"
        )
