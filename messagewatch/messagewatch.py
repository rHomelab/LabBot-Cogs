from typing import Optional

import discord
from redbot.core import Config, checks
from redbot.core.bot import Red
from redbot.core import commands
from redbot.core.utils.mod import is_mod_or_superior


class MessageWatchCog(commands.Cog):
    """MessageWatch Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384004)
        self.alertCache = {}
        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "recent_fetch_time": 15000,  # Time, in milliseconds, to fetch recent prior messages used for calculations.
            "frequencies": {  # Collection of allowable frequencies
                "embed": 1  # Allowable frequency for embeds
            },
            "exemptions": {
                "member_duration": 30,  # Minimum member joined duration required to qualify for any exemptions
                "text_messages": 1,  # Minimum text-only message frequency required to exempt a user
            }
        }

        self.config.register_guild(**default_guild_config)

    @checks.admin()
    @commands.group("messagewatch", aliases=["mw"], pass_context=True)
    async def _messagewatch(self, ctx: commands.Context):
        pass

    @_messagewatch.command(name="logchannel")
    async def _logchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
        """Set/update the channel to send message activity alerts to."""

        chanId = ctx.channel.id
        if channel:
            chanId = channel.id
        await self.config.guild(ctx.guild).logchannel.set(chanId)
        await ctx.send("✅ Alert channel successfully updated!")

    @_messagewatch.command(name="fetchtime")
    async def _fetch_time(self, ctx: commands.Context, time: str):
        """Set/update the recent message fetch time (in milliseconds)."""
        try:
            val = float(time)
            await self.config.guild(ctx.guild).recent_fetch_time.set(val)
            await ctx.send("Recent message fetch time successfully updated!")
        except ValueError:
            await ctx.send("Recent message fetch time FAILED to update. Please specify a `float` value only!")

    @_messagewatch.group("frequencies", aliases=["freq", "freqs"])
    async def _messagewatch_frequencies(self, ctx: commands.Context):
        pass

    @_messagewatch_frequencies.command(name="embed")
    async def _fetch_time(self, ctx: commands.Context, frequency: str):
        """Set/update the allowable embed frequency."""
        try:
            val = float(frequency)
            await self.config.guild(ctx.guild).frequencies.embed.set(val)
            await ctx.send("Allowable embed frequency successfully updated!")
        except ValueError:
            await ctx.send("Allowable embed frequency FAILED to update. Please specify a `float` value only!")

    @_messagewatch.group("exemptions", aliases=["exempt", "exempts"])
    async def _messagewatch_exemptions(self, ctx: commands.Context):
        pass

    @_messagewatch_exemptions.command(name="member_duration", aliases="md")
    async def _fetch_time(self, ctx: commands.Context, time: str):
        """Set/update the minimum member duration, in hours, to qualify for exemptions."""
        try:
            val = int(time)
            await self.config.guild(ctx.guild).exemptions.member_duration.set(val)
            await ctx.send("Minimum member duration successfully updated!")
        except ValueError:
            await ctx.send("Minimum member duration FAILED to update. Please specify a `integer` value only!")

    @_messagewatch_exemptions.command(name="text_messages", aliases="text")
    async def _fetch_time(self, ctx: commands.Context, frequency: str):
        """Set/update the minimum frequency of text-only messages to be exempt."""
        try:
            val = float(frequency)
            await self.config.guild(ctx.guild).exemptions.text_messages.set(val)
            await ctx.send("Text-only message frequency exemption successfully updated!")
        except ValueError:
            await ctx.send("Text-only message frequency exemption FAILED to update. Please specify a `float` value "
                           "only!")

    @commands.Cog.listener()
    async def on_message(self, ctx: commands.Context, message: discord.Message):
        if is_mod_or_superior(self.bot, message):  # Automatically exempt mods/admin
            return
        pass
