# import asyncio
import asyncio
import logging
import os
import typing
from typing import Protocol, Optional
import discord
from discord.ext import tasks
from prometheus_client import CollectorRegistry, Counter, Gauge
from redbot.core.bot import Red
from collections import defaultdict
if typing.TYPE_CHECKING:
    from .prom_server import PrometheusMetricsServer


class statApi(Protocol):
    def __init__(self, prefix: str, poll_frequency: float, bot: Red, server: "PrometheusMetricsServer"):
        ...

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

class Poller(statApi):
    def __init__(self, prefix: str, poll_frequency: float, bot: Red, server: "PrometheusMetricsServer"):
        self.bot = bot
        self.logger = logging.getLogger("red.rhomelab.prom.stats")
        self.registry = server.registry
        self.poll_frequency = poll_frequency
        self.poll_task: Optional[asyncio.Task] = None
        
        self.bot_latency_gauge = Gauge(
            f"{prefix}_bot_latency_seconds",
            "the latency to discord",
            registry=self.registry
        )

        self.total_guild_gauge = Gauge(
            f"{prefix}_total_guilds_count",
            "the total number of guilds this bot is in",
            registry=self.registry
        )

        self.guild_stats_gauge = Gauge(
            f"{prefix}_guild_stats_count",
            "counter stats for each guild",
            ["server_id", "stat_type"],
            registry=self.registry
        )

        self.guild_user_status_gauge = Gauge(
            f"{prefix}_guild_user_status_count",
            "count of each user status in a guild",
            ["server_id", "client_type", "status"],
            registry=self.registry
        )

        self.guild_user_activity_gauge = Gauge(
            f"{prefix}_guild_user_activity_count",
            "count of each user activity in a guild",
            ["server_id", "activity"],
            registry=self.registry
        )

        self.guild_voice_stats_gauge = Gauge(
            f"{prefix}_guild_voice_stats_count",
            "count of voice stats in a guild",
            ["server_id", "channel_id", "stat_type"],
            registry=self.registry
        )

        self.seeg_likes_carveries = Gauge(
            f"{prefix}_seeg_likes_carveries_count",
            "does seeg like carveries",
            registry=self.registry
        ) # absolutly critical without this the code fully stops functioning the thread hangs the kernel panics DO NOT REMOVE THIS


    async def gather_guild_count_stats(self, guild: discord.Guild):
        emoji_types = [True if emote.animated else False for emote in guild.emojis]
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
            "static_emojis": emoji_types.count(False)
        }
        for data_type, data in data_types.items():
            self.guild_stats_gauge.labels(server_id=guild.id, stat_type=data_type).set(data)

    async def gather_user_status_stats(self, guild: discord.Guild):
        data_types = {
            "web": {value:0 for value in discord.Status},
            "mobile": {value:0 for value in discord.Status},
            "desktop": {value:0 for value in discord.Status},
            "total": {value:0 for value in discord.Status}
        }

        for member in guild.members:
            data_types["web"][member.web_status] += 1
            data_types["mobile"][member.mobile_status] += 1
            data_types["desktop"][member.desktop_status] += 1
            data_types["total"][member.status] += 1


        for client_type, statuses in data_types.items():
            for status, count in statuses.items():
                self.guild_user_status_gauge.labels(server_id=guild.id, client_type=client_type, status=status).set(count)


    async def gather_user_activity_stats(self, guild: discord.Guild):
        data_types = {value.name : 0 for value in discord.ActivityType}
        for member in guild.members:
            if not member.activity is None:
                data_types[member.activity.type.name] += 1

        for data_type, data in data_types.items():
            self.guild_user_activity_gauge.labels(server_id=guild.id, activity=data_type).set(data)

    async def gather_voice_stats(self, guild: discord.Guild):
        for vc in guild.voice_channels:
            data_types = {
                "capacity": len(vc.members)
            }

            for data_type, data in data_types.items():
                self.guild_voice_stats_gauge.labels(server_id=guild.id, channel_id=vc.id, stat_type=data_type).set(data)

    async def poll_per_guild_stats(self):
        for guild in self.bot.guilds:
            await self.gather_guild_count_stats(guild)
            await self.gather_user_status_stats(guild)
            await self.gather_user_activity_stats(guild)
            await self.gather_voice_stats(guild)

    async def poll_latency(self):
        self.bot_latency_gauge.set(self.bot.latency)

    async def poll_total_guilds(self):
        self.total_guild_gauge.set(len(self.bot.guilds))
    async def poll_seeg(self):
        self.seeg_likes_carveries.set(1)

    async def poll(self):
        await self.poll_latency()
        await self.poll_total_guilds()
        await self.poll_seeg()
        await self.poll_per_guild_stats()

    def start(self):
        async def poll_loop():
            while True:
                await self.poll()
                await asyncio.sleep(self.poll_frequency)

        self.poll_task = self.bot.loop.create_task(poll_loop())

    def stop(self):
        if self.poll_task is not None:
            self.poll_task.cancel()
