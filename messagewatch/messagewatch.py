from datetime import datetime, timedelta, timezone
from typing import Optional, List

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
        self.embed_speeds = {}
        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "recent_fetch_time": 15000,  # Time in milliseconds to fetch recent prior embed times used for calculations.
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
    async def _messagewatch_logchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
        """Set/update the channel to send message activity alerts to."""

        chanId = ctx.channel.id
        if channel:
            chanId = channel.id
        await self.config.guild(ctx.guild).logchannel.set(chanId)
        await ctx.send("✅ Alert channel successfully updated!")

    @_messagewatch.command(name="fetchtime")
    async def _messagewatch_fetchtime(self, ctx: commands.Context, time: str):
        """Set/update the recent message fetch time (in milliseconds)."""
        try:
            val = float(time)
            await self.config.guild(ctx.guild).recent_fetch_time.set(val)
            await ctx.send("Recent message fetch time successfully updated!")
        except ValueError:
            await ctx.send("Recent message fetch time FAILED to update. Please specify a `float` value only!")

    @_messagewatch.group("frequencies", aliases=["freq", "freqs"], pass_context=True)
    async def _messagewatch_frequencies(self, ctx: commands.Context):
        pass

    @_messagewatch_frequencies.command(name="embed")
    async def _messagewatch_frequencies_embed(self, ctx: commands.Context, frequency: str):
        """Set/update the allowable embed frequency."""
        try:
            val = float(frequency)
            await self.config.guild(ctx.guild).frequencies.embed.set(val)
            await ctx.send("Allowable embed frequency successfully updated!")
        except ValueError:
            await ctx.send("Allowable embed frequency FAILED to update. Please specify a `float` value only!")

    @_messagewatch.group("exemptions", aliases=["exempt", "exempts"], pass_context=True)
    async def _messagewatch_exemptions(self, ctx: commands.Context):
        pass

    @_messagewatch_exemptions.command(name="memberduration", aliases=["md"])
    async def _messagewatch_exemptions_memberduration(self, ctx: commands.Context, time: str):
        """Set/update the minimum member duration, in hours, to qualify for exemptions."""
        try:
            val = int(time)
            await self.config.guild(ctx.guild).exemptions.member_duration.set(val)
            await ctx.send("Minimum member duration successfully updated!")
        except ValueError:
            await ctx.send("Minimum member duration FAILED to update. Please specify a `integer` value only!")

    @_messagewatch_exemptions.command(name="textmessages", aliases=["text"])
    async def _messagewatch_expemptions_textmessages(self, ctx: commands.Context, frequency: str):
        """Set/update the minimum frequency of text-only messages to be exempt."""
        try:
            val = float(frequency)
            await self.config.guild(ctx.guild).exemptions.text_messages.set(val)
            await ctx.send("Text-only message frequency exemption successfully updated!")
        except ValueError:
            await ctx.send("Text-only message frequency exemption FAILED to update. Please specify a `float` value "
                           "only!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await is_mod_or_superior(self.bot, message):  # Automatically exempt mods/admin
            return
        for i in range(len(message.attachments)):
            await self.add_embed_time(message.guild, message.author, datetime.utcnow())  # TODO: Use message timestamp
        for i in range(len(message.embeds)):
            await self.add_embed_time(message.guild, message.author, datetime.utcnow())  # TODO: Use message timestamp
        await self.analyze_speed(message.guild, message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if await is_mod_or_superior(self.bot, before):  # Automatically exempt mods/admins
            return
        total_increase = len(after.attachments) - len(before.attachments)
        total_increase += len(after.embeds) - len(before.attachments)
        if total_increase > 0:
            for i in range(total_increase):
                await self.add_embed_time(after.guild,  # Use the ctx guild because edits are inconsistent, TODO: Message time
                                    after.author if after.author is not None else before.author, datetime.utcnow())
            await self.analyze_speed(after.guild, after)

    async def get_embed_times(self, guild: discord.Guild, user: discord.User) -> List[datetime]:
        if guild.id not in self.embed_speeds:
            self.embed_speeds[guild.id] = {}
        if user.id not in self.embed_speeds[guild.id]:
            self.embed_speeds[guild.id][user.id] = []
        return self.embed_speeds[guild.id][user.id]

    async def add_embed_time(self, guild: discord.Guild, user: discord.User, time: datetime):
        await self.get_embed_times(guild, user)  # Call to get the times to build the user's cache if not already exists
        self.embed_speeds[guild.id][user.id].append(time)

    async def get_recent_embed_times(self, guild: discord.Guild, user: discord.User) -> List[datetime]:
        filter_time = datetime.utcnow() - timedelta(milliseconds=await self.config.guild(guild).recent_fetch_time())
        return [time for time in await self.get_embed_times(guild, user) if time >= filter_time]

    async def analyze_speed(self, guild: discord.Guild, trigger: discord.Message):
        """Analyzes the frequency of embeds  & attachments by a user. Should only be called upon message create/edit."""
        embed_times = await self.get_recent_embed_times(guild, trigger.author)
        if len(embed_times) < 2:
            return  # Return because we don't have enough data to calculate the frequency
        first_time = embed_times[0]
        last_time = embed_times[len(embed_times) - 1]
        embed_frequency = len(embed_times) / (last_time - first_time).microseconds  # may need to convert to nano
        if embed_frequency > await self.config.guild(guild).frequencies.embed():
            # Alert triggered, send unless exempt

            # Membership duration exemption
            allowable = trigger.author.joined_at + timedelta(
                hours=await self.config.guild(guild).exemptions.member_duration())
            if datetime.now(timezone.utc) < allowable:
                return

            # Text-only message exemption (aka active participation exemption)
            # TODO

            # No exemptions at this point, alert!
            # Credit: Taken from report Cog
            log_id = await self.config.guild(guild).logchannel()
            log = None
            if log_id:
                log = guild.get_channel(log_id)
            if not log:
                # Failed to get the channel
                return

            data = self.make_alert_embed(trigger.author, trigger)

            mod_pings = " ".join(
                [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
            if not mod_pings:  # If no online/idle mods
                mod_pings = " ".join([i.mention for i in log.members if not i.bot])

            await log.send(content=mod_pings, embed=data)
            # End credit
    def make_alert_embed(self, member: discord.Member, message: discord.Message) -> discord.Embed:
        """Construct the alert embed to be sent"""
        # Copied from the report Cog.
        return (
            discord.Embed(
                colour=discord.Colour.orange(),
                description="High frequency of embeds detected from a user."
            )
            .set_author(name="Suspicious User Activity", icon_url=member.avatar.url)
            .add_field(name="Server", value=member.guild.name)
            .add_field(name="User", value=member.mention)
            .add_field(name="Message",
                       value=f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}")
            .add_field(name="Timestamp", value=f"<t:{int(datetime.now().utcnow().timestamp())}:F>")
        )