from datetime import datetime
from typing import Optional

import croniter
import discord
from redbot.core import Config


class ConfigHelper:
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

    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """
        Fetches the log channel from config,
        then fetches the channel from the client cache.
        If the channel is set, but cannot be fetched, the config value will be reset.
        """
        channel_id: Optional[int] = await self.config.guild(guild).logchannel()
        if channel_id is None:
            return

        channel: Optional[discord.TextChannel] = guild.get_channel(channel_id)
        if channel is not None:
            return channel

        await self.config.guild(guild).logchannel.set(None)

    async def set_log_channel(self, guild: discord.Guild, channel: discord.TextChannel):
        """Sets the log channel config value to the ID of the channel."""
        await self.config.guild(guild).logchannel.set(channel)

    async def member_is_excluded(self, guild: discord.Guild, member: discord.Member) -> bool:
        """
        Fetch whether a member is part of the exclude list or not
        (members who will not be included in the purge, even if they are otherwise eligible.)
        """
        return member.id in await self.config.guild(guild).excludedusers()

    async def add_excluded_member(self, guild: discord.Guild, member: discord.Member):
        """Adds a member to the exclude list."""
        async with self.config.guild(guild).excludedusers() as excluded_users:
            if member.id not in excluded_users:
                excluded_users.append(member.id)

    async def remove_excluded_member(self, guild: discord.Guild, member: discord.Member):
        """Removes a member from the exclude list."""
        async with self.config.guild(guild).excludedusers() as excluded_users:
            excluded_users.remove(member.id)

    async def get_age_threshold(self, guild: discord.Guild) -> int:
        """Fetches the config value for how many days a member can go without verifying before they are purgeable."""
        return await self.config.guild(guild).minage()

    async def set_age_threshold(self, guild: discord.Guild, threshold: int):
        """Sets the age threshold config value."""
        await self.config.guild(guild).minage.set(threshold)

    async def get_count(self, guild: discord.Guild) -> int:
        """Fetch the total number of members purged from this guild."""
        return await self.config.guild(guild).count()

    async def increment_count(self, guild: discord.Guild, *, increment_by: int = 1):
        """Increment the member count by the given amount (1 by default)."""
        config_group = self.config.guild(guild)
        await config_group.count.set(await config_group.count() + increment_by)

    async def get_last_run(self, guild: discord.Guild) -> Optional[datetime]:
        """Fetch a datetime object representing the time that the last purge was run at."""
        last_run_timestamp = await self.config.guild(guild).lastrun()
        return datetime.utcfromtimestamp(last_run_timestamp) if last_run_timestamp is not None else None

    async def set_last_run(self, guild: discord.Guild):
        """Sets the last run timestamp to the current datetime."""
        now = datetime.utcnow()
        await self.config.guild(guild).lastrun.set(int(now.timestamp()))

    async def get_next_run(self, guild: discord.Guild) -> Optional[datetime]:
        """
        Calculates the next run timestamp from the schedule and last run values.
        Returns None if purge is disabled, or has not been run yet.
        """
        last_run = await self.get_last_run(guild)
        if last_run is None:
            return None

        if not await self.is_enabled(guild):
            return None

        schedule = await self.get_schedule(guild)
        return schedule.get_next(datetime)

    async def is_enabled(self, guild: discord.Guild) -> bool:
        """Returns a bool representing whether the cog is enabled in this guild or not."""
        return await self.config.guild(guild).enabled()

    async def enable(self, guild: discord.Guild):
        """Enable the cog in this guild."""
        await self.config.guild(guild).enabled.set(True)

    async def disable(self, guild: discord.Guild):
        """Disable the cog in this guild."""
        await self.config.guild(guild).enabled.set(False)

    async def get_schedule(self, guild: discord.Guild) -> croniter.croniter:
        """Fetch the cron schedule for this guild."""
        return croniter.croniter(await self.config.guild(guild).schedule())

    async def set_schedule(self, guild: discord.Guild, cron_expression: str) -> bool:
        """
        Sets the cron expression for this guild.
        Returns a bool stating whether the cron expression is valid.
        If not valid, the value won't be persisted to config.
        """
        if croniter.croniter.is_valid(cron_expression):
            await self.config.guild(guild).schedule.set(cron_expression)
            return True
        else:
            return False

    async def should_run(self, guild: discord.Guild) -> bool:
        """
        Determine whether the purge task for this guild is ready to be run.
        This relies on the following being true:
        - Cog is enabled for the guild
        - Current time is past the next scheduled time
        - Bot has guild permissions to kick members
        - Log channel has been configured and is valid
        """
        return (
            await self.is_enabled(guild)
            and await self.get_next_run(guild) > datetime.utcnow()
            and guild.me.guild_permissions.kick_members
            and await self.config.get_log_channel(guild) is not None
        )
