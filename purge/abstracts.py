from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import croniter
import discord
from redbot.core import Config


class ConfigHelperABC(ABC):
    config: Config

    def __init__(self):
        self.config = Config.get_conf(self, identifier=489182828)
        default_guild_settings = {
            "excludedusers": [],  # list[int]
            "minage": 5,  # int
            "schedule": "0 */6 * * *",  # str
            "count": 0,  # int
            "lastrun": None,  # int
            "enabled": False,  # bool
            "logchannel": None,  # int
        }

        self.config.register_guild(**default_guild_settings)

    @abstractmethod
    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """
        Fetches the log channel from config,
        then fetches the channel from the client cache.
        If the channel is set, but cannot be fetched, the config value will be reset.
        """

    @abstractmethod
    async def set_log_channel(self, guild: discord.Guild, channel: discord.TextChannel):
        """Sets the log channel config value to the ID of the channel."""

    @abstractmethod
    async def member_is_excluded(self, guild: discord.Guild, member: discord.Member) -> bool:
        """
        Fetch whether a member is part of the exclude list or not
        (members who will not be included in the purge, even if they are otherwise eligible.)
        """

    @abstractmethod
    async def add_excluded_member(self, guild: discord.Guild, member: discord.Member):
        """Adds a member to the exclude list."""

    @abstractmethod
    async def remove_excluded_member(self, guild: discord.Guild, member: discord.Member):
        """Removes a member from the exclude list."""

    @abstractmethod
    async def get_age_threshold(self, guild: discord.Guild) -> int:
        """Fetches the config value for how many days a member can go without verifying before they are purgeable."""

    @abstractmethod
    async def set_age_threshold(self, guild: discord.Guild, threshold: int):
        """Sets the age threshold config value."""

    @abstractmethod
    async def get_count(self, guild: discord.Guild) -> int:
        """Fetch the total number of members purged from this guild."""

    @abstractmethod
    async def increment_count(self, guild: discord.Guild, *, increment_by: int = 1):
        """Increment the member count by the given amount (1 by default)."""

    @abstractmethod
    async def get_last_run(self, guild: discord.Guild) -> Optional[datetime]:
        """Fetch a datetime object representing the time that the last purge was run at."""

    @abstractmethod
    async def set_last_run(self, guild: discord.Guild):
        """Sets the last run timestamp to the current datetime."""

    @abstractmethod
    async def get_next_run(self, guild: discord.Guild) -> Optional[datetime]:
        """
        Calculates the next run timestamp from the schedule and last run values.
        Returns None if purge is disabled, or has not been run yet.
        """

    @abstractmethod
    async def is_enabled(self, guild: discord.Guild) -> bool:
        """Returns a bool representing whether the cog is enabled in this guild or not."""

    @abstractmethod
    async def enable(self, guild: discord.Guild):
        """Enable the cog in this guild."""

    @abstractmethod
    async def disable(self, guild: discord.Guild):
        """Disable the cog in this guild."""

    @abstractmethod
    async def get_schedule(self, guild: discord.Guild) -> croniter.croniter:
        """Fetch the cron schedule for this guild."""

    @abstractmethod
    async def set_schedule(self, guild: discord.Guild, cron_expression: str) -> bool:
        """
        Sets the cron expression for this guild.
        Returns a bool stating whether the cron expression is valid.
        If not valid, the value won't be persisted to config.
        """
