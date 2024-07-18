import asyncio
import logging
import typing
from typing import Optional, Protocol

import discord
from prometheus_client import Gauge
from redbot.core.bot import Red

from .utils import timeout

logger = logging.getLogger("red.rhomelab.prom.stats")

if typing.TYPE_CHECKING:
    from .prom_server import PrometheusMetricsServer


class statApi(Protocol):
    def __init__(self, prefix: str, poll_frequency: int, bot: Red, server: "PrometheusMetricsServer"): ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class Poller(statApi):
    def __init__(self, prefix: str, poll_frequency: int, bot: Red, server: "PrometheusMetricsServer"):
        self.bot = bot
        self.registry = server.registry
        self.poll_frequency = poll_frequency
        self.poll_task: Optional[asyncio.Task] = None

        self.bot_latency_gauge = Gauge(f"{prefix}_bot_latency_seconds", "the latency to discord", registry=self.registry)

        self.total_guild_gauge = Gauge(
            f"{prefix}_total_guilds_count", "the total number of guilds this bot is in", registry=self.registry
        )

        self.guild_stats_gauge = Gauge(
            f"{prefix}_guild_stats_count", "counter stats for each guild", ["server_id", "stat_type"], registry=self.registry
        )

        self.guild_user_status_gauge = Gauge(
            f"{prefix}_guild_user_status_count",
            "count of each user status in a guild",
            ["server_id", "client_type", "status"],
            registry=self.registry,
        )

        self.guild_user_activity_gauge = Gauge(
            f"{prefix}_guild_user_activity_count",
            "count of each user activity in a guild",
            ["server_id", "activity"],
            registry=self.registry,
        )

        self.guild_voice_stats_gauge = Gauge(
            f"{prefix}_guild_voice_stats_count",
            "count of voice stats in a guild",
            ["server_id", "channel_id", "stat_type"],
            registry=self.registry,
        )

    @timeout
    async def gather_guild_count_stats(self, guild: discord.Guild):
        logger.debug("gathering guild count stats")
        emoji_types = [emote.animated for emote in guild.emojis]
        data_types = {
            "members": len(guild.members),
            "voice_channels": len(guild.voice_channels),
            "text_channels": len(guild.text_channels),
            "categories": len(guild.categories),
            "stage_channels": len(guild.stage_channels),
            "forums": len(guild.forums),
            "roles": len(guild.roles),
            "emojis": len(guild.emojis),
            "animated_emojis": emoji_types.count(True),
            "static_emojis": emoji_types.count(False),
        }
        for data_type, data in data_types.items():
            logger.debug("setting guild stats gauge server_id:%d, stat_type:%s, data:%s", guild.id, data_type, data)
            self.guild_stats_gauge.labels(server_id=guild.id, stat_type=data_type).set(data)

    @timeout
    async def gather_user_status_stats(self, guild: discord.Guild):
        logger.debug("gathering user status count")
        data_types = {
            "web": {value: 0 for value in discord.Status},
            "mobile": {value: 0 for value in discord.Status},
            "desktop": {value: 0 for value in discord.Status},
            "total": {value: 0 for value in discord.Status},
        }

        for member in guild.members:
            data_types["web"][member.web_status] += 1
            data_types["mobile"][member.mobile_status] += 1
            data_types["desktop"][member.desktop_status] += 1
            data_types["total"][member.status] += 1

        for client_type, statuses in data_types.items():
            for status, count in statuses.items():
                logger.debug(
                    "setting user status gauge server_id:%d, client_type:%s, status:%s, data:%d",
                    guild.id,
                    client_type,
                    status,
                    count,
                )
                self.guild_user_status_gauge.labels(server_id=guild.id, client_type=client_type, status=status).set(count)

    @timeout
    async def gather_user_activity_stats(self, guild: discord.Guild):
        logger.debug("gathering user activity stats")
        data_types = {value.name: 0 for value in discord.ActivityType if "unknown" not in value.name}

        for member in guild.members:
            if member.activity is not None and member.activity.type.name in data_types:
                data_types[member.activity.type.name] += 1
                logger.debug("post user activity stats collection")

        for data_type, data in data_types.items():
            logger.debug(
                "setting user activity gauge server_id:%d, activity:%s, data:%d",
                guild.id,
                data_type,
                data,
            )
            self.guild_user_activity_gauge.labels(server_id=guild.id, activity=data_type).set(data)

    @timeout
    async def gather_voice_stats(self, guild: discord.Guild):
        logger.debug("gathering voice stats")
        logger.debug("voice channel count: %d", len(guild.voice_channels))

        for vc in guild.voice_channels:
            data_types = {"capacity": len(vc.members)}

            for data_type, data in data_types.items():
                logger.debug(
                    "setting voice stats gauge server_id:%d, channel_id:%s, stat_type:%s, data:%d",
                    guild.id,
                    vc.id,
                    data_type,
                    data,
                )
                self.guild_voice_stats_gauge.labels(server_id=guild.id, channel_id=vc.id, stat_type=data_type).set(data)

    async def poll_per_guild_stats(self):
        for guild in self.bot.guilds:
            await self.gather_guild_count_stats(guild)
            await self.gather_user_status_stats(guild)
            await self.gather_user_activity_stats(guild)
            await self.gather_voice_stats(guild)

    @timeout
    async def poll_latency(self):
        logger.debug("setting bot latency guage: %d", self.bot.latency)
        self.bot_latency_gauge.set(self.bot.latency)

    @timeout
    async def poll_total_guilds(self):
        logger.debug("setting total guild guage: %d", len(self.bot.guilds))

        self.total_guild_gauge.set(len(self.bot.guilds))

    async def poll(self):
        logger.debug("running polling run")
        await self.poll_latency()
        await self.poll_total_guilds()
        await self.poll_per_guild_stats()

    def start(self):
        async def poll_loop():
            while True:
                await self.poll()
                await asyncio.sleep(self.poll_frequency)

        logger.debug("creating polling loop")

        self.poll_task = self.bot.loop.create_task(poll_loop())

    def stop(self):
        logger.debug("tearing down polling loop")
        if self.poll_task is not None:
            logger.debug("cancelling polling loop")

            self.poll_task.cancel()
