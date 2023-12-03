import logging

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red

from .prom_server import PrometheusMetricsServer, promServer
from .stats import Poller, statApi

logger = logging.getLogger("red.rhomelab.prom")
logger.setLevel(logging.DEBUG)

class PromExporter(commands.Cog):
    """commands for managing the prom exporter"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.rhomelab.prom")
        self.logger.info("initalising")
        self.address = "0.0.0.0"
        self.port = 9000
        self.poll_frequency = 1

        self.config = Config.get_conf(self, identifier=19283750192891838)

        default_global= {
            "address": "0.0.0.0",
            "port": 9900,
            "poll_interval": 1
        }
        self.config.register_global(**default_global)

        self.prom_server = None
        self.stat_api = None

    async def init(self):
        self.address = await self.config.address()
        self.port = await self.config.port()
        self.poll_frequency = await self.config.poll_interval()
        self.start()

    @staticmethod
    def create_server(address: str, port: int):
        return promServer(address, port)

    @staticmethod
    def create_stat_api(prefix: str, poll_frequency: float, bot: Red, server: PrometheusMetricsServer) -> statApi:
        return Poller(prefix, poll_frequency, bot, server)

    @commands.group()
    async def prom_export(self, ctx: commands.Context):
        """Red Bot Prometheus Exporter"""

    @checks.is_owner()
    @prom_export.command()
    async def set_port(self, ctx: commands.Context, port: int):
        """Set the port the exporter should listen on"""
        self.logger.info(f"changing port to {port}")
        self.port = port
        await self.config.port.set(port)
        self.reload()
        await ctx.tick()


    @checks.is_owner()
    @prom_export.command()
    async def set_address(self, ctx: commands.Context, address: str):
        """Set the address the exporter should listen on"""

        self.logger.info(f"changing address to {address}")

        self.address = address
        await self.config.address.set(address)
        self.reload()
        await ctx.tick()


    @checks.is_owner()
    @prom_export.command()
    async def set_poll_interval(self, ctx: commands.Context, poll_interval: float):
        """Set the metrics poll interval (seconds)"""

        self.logger.info(f"changing poll interval to {poll_interval}")
        self.poll_frequency = poll_interval
        await self.config.poll_interval.set(poll_interval)
        self.reload()
        await ctx.tick()

    @checks.is_owner()
    @prom_export.command(name="config")
    async def show_config(self, ctx: commands.Context):
        """Show the current config"""
        conf_embed = (discord.Embed(title="Role info", colour=await ctx.embed_colour())
            .add_field(name="Address", value=self.address)
            .add_field(name="Port", value=self.port)
            .add_field(name="Poll Frequency", value=self.poll_frequency)
        )
        await ctx.send(embed=conf_embed)


    def start(self):
        self.prom_server = self.create_server(self.address, self.port)
        self.stat_api = self.create_stat_api("discord_metrics", self.poll_frequency, self.bot, self.prom_server)

        self.prom_server.serve()
        self.stat_api.start()

    def stop(self):
        self.prom_server.stop()
        self.stat_api.stop()
        self.logger.info("stopped server process")

    def reload(self):
        self.logger.info("reloading")
        self.stop()
        self.start()
        self.logger.info("reloading complete")

    def cog_unload(self):
        self.stop()
        self.logger.info("cog unloading")
