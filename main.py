#!/bin/python3

from logging import Logger, getLogger, handlers, Formatter
from discord import Intents
from discord.bot import Bot
import sentry_sdk
import logging

from configparser import ConfigParser
from cogs.observer import Observer
from utils.logger import AppLogger
from EVA import Eva

appLogger = AppLogger()
appLogger.setup()
logger = appLogger.logger

# DEFINE CONFIGS
logger.debug("Loading configs")
CONFIG = ConfigParser()
CONFIG.read("./config.ini")
TOKEN = CONFIG["TOKENS"]["discord"]
GUILDS = CONFIG["GUILDS"]["MyGuilds"]
OPEN_AI = CONFIG["TOKENS"]["open_ai"]
SENTRY_DSN = CONFIG["TOKENS"]["sentry_dsn"]
logger.debug("Configs loaded")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

intents = Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.members = True


eva = Bot(
    intents=intents,
    debug_guilds=[GUILDS],
    auto_sync_commands=True,
)


@eva.event
async def on_ready():
    logger.info((f"{eva.user.name} Ready!"))
    print(f"--- {eva.user.name} ({eva.user.display_name}) [{eva.latency} ms]")


# Register cogs
# MAIN BOT
eva.add_cog(Eva(eva))
# Aditional Cogs
COGS = [
    Observer(eva),
]
for cog in COGS:
    logger.debug(f"Adding Cog {cog.description} to the Bot")
    eva.add_cog(cog)

# RUN
eva.run(TOKEN)
