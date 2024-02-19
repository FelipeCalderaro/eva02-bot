import asyncio
import logging
import discord

from discord.ext import commands
from utils.logger import AppLogger


class Player:
    """Player used to join voice channels and reproduce audio"""

    voice_channel: discord.VoiceClient = None

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self._logger = AppLogger().logger
        self.bot = bot
        self._logger.log(logging.INFO, "Starting the Player class")

    async def join(self, channel: discord.VoiceChannel):
        try:
            self.voice_channel = await channel.connect()
            self._logger.log(
                logging.INFO,
                f"Joined? {self.voice_channel.is_connected()}",
            )

        except discord.errors.ClientException:
            self._logger.warning("Client already connected to a voice channel")
            print(f"Current voice clients: {self.bot.voice_clients}")
            self.voice_channel = self.bot.voice_clients[-1]

    async def leave(self):
        if self.voice_channel == None:
            self.voice_channel = self.bot.voice_clients[-1]
        self.voice_channel.cleanup()
        await self.voice_channel.disconnect()

    async def wait_play_finish(self, delay: float = 0.2):
        while self.voice_channel.is_playing():
            await asyncio.sleep(delay)
        try:
            await self.leave()
        except Exception:
            pass

    async def warm_up(self):
        self.voice_channel.play()

    def is_connected(self) -> bool:
        return self.voice_channel != None

    async def play(
        self,
        file: str | None = None,
        path: str | None = None,
        leave_after_play: bool = True,
    ):
        if self.voice_channel.is_connected():
            self._logger.log(logging.INFO, "Connected, playing now...")

        self.voice_channel.play(
            discord.FFmpegPCMAudio(
                executable="/usr/bin/ffmpeg",
                source=f"/audios/{file}" if path is None else path,
            ),
        )
        if leave_after_play:
            asyncio.create_task(self.wait_play_finish())
