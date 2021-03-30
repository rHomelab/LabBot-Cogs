"""discord red-bot uptimestats"""
from datetime import datetime as dt
from datetime import strftime, timedelta
from typing import Tuple

import discord
from redbot.core import commands


class UptimeStatsCog(commands.Cog):
    """Uptime Stats cog"""

    def __init__(self, bot):
        self.bot = bot
        self.cmd_count = 0
        self.msg_count = 0
        self.disconnects = []
        self.start_time = dt.now()

    # Events

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        """Command event for all commands"""
        self.cmd_count += 1

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Message event for all messages"""
        self.msg_count += 1

    @commands.Cog.listener()
    async def on_disconnect(self):
        """API Disconnect event"""
        self.disconnects.append(dt.now())

    # Commands

    @commands.command("uptimestats")
    async def uptime_stats(self, ctx: commands.Context):
        embed = await self.make_stats_embed()
        await ctx.send(embed=embed)

    # Helper functions

    async def make_stats_embed(self, ctx) -> discord.Embed:
        embed = discord.Embed(title="Uptime stats", colour=await ctx.embed_colour())
        embed.add_field(
            name="Uptime",
            value=self.uptime_from_delta(dt.now() - self.start_time),
            inline=False,
        )
        embed.add_field(name="Latency", value=f"{ctx.bot.latency * 1000}ms")
        embed.add_field(name="Commands Executed", value=self.cmd_count)
        embed.add_field(name="Messages Processed", value=self.msg_count)
        embed.add_field(name="Disconnects", value=len(self.disconnects))
        embed.add_field(name="Last Disconnect Time", value=self.disconnects[-1])

    def uptime_from_delta(self, delta: timedelta) -> Tuple[int]:
        days = delta.days
        hours = delta.seconds // 60 // 60
        minutes = delta.seconds // 60 % 60
        seconds = delta.seconds % 60
        return f"{days} days, {hours} hours, {minutes} minutes and {seconds} seconds"
