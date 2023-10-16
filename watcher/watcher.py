from datetime import timedelta, timezone, datetime
from typing import Optional, List

import discord
import re
from redbot.core import Config, checks
from redbot.core.bot import Red
from redbot.core.commands import commands
from redbot.core.utils.chat_formatting import pagify, escape
from redbot.core.utils.menus import menu, prev_page, close_menu, next_page
from redbot.core.utils.mod import is_mod_or_superior


class WatcherCog(commands.Cog):
    """Watcher Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384001)
        self.embed_speeds = {}
        self.alert_cache = {}
        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "messagewatcher": {
                "recent_fetch_time": 15000,  # Time (milliseconds) to fetch recent embed times used for calculations.
                "frequencies": {  # Collection of allowable frequencies
                    "embed": 1  # Allowable frequency for embeds
                },
                "exemptions": {
                    "member_duration": 30,  # Minimum member joined duration required to qualify for any exemptions
                    "text_messages": 1,  # Minimum text-only message frequency required to exempt a user
                }
            },
            "voicewatcher": {
                "min_joined_hours": 8760  # Default to one year so the mods set it up :)
            },
            "profilewatcher": {
                "rules": {
                    "spammer1": {  # Name of rule
                        "pattern": "^portalBlock$",  # Regex pattern to match against
                        "check_nick": False,  # Whether the user's nickname should be checked too
                        "alert_level": "HIGH",  # Severity of alerts (use: HIGH or LOW)
                        "reason": "Impostor :sus:"  # Reason for the match, used to add context to alerts
                    }
                }
            }
        }

        self.config.register_guild(**default_guild_config)

    @checks.admin()
    @commands.group("watcher", pass_context=True)
    async def _watcher(self, ctx: commands.Context):
        pass

    @_watcher.command(name="logchannel")
    async def _logchannel(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
        """Set/update the channel to send activity alerts to."""

        chanId = ctx.channel.id
        if channel:
            chanId = channel.id
        await self.config.guild(ctx.guild).logchannel.set(chanId)
        await ctx.send("✅ Alert channel successfully updated!")

    @_watcher.group("voicewatch", aliases=["vw"], pass_context=True)
    async def _voicewatch(self, ctx: commands.Context):
        pass

    @_voicewatch.command(name="time")
    async def _voicewatch_time(self, ctx: commands.Context, hours: str):
        """Set/update the minimum hours users must be in the server before without triggering an alert."""
        try:
            hrs = int(hours)
            await self.config.guild(ctx.guild).voicewatcher.min_joined_hours.set(hrs)
            await ctx.send("✅ Time requirement successfully updated!")
        except ValueError:
            await ctx.send("Error: Non-number hour argument supplied.")

    @_watcher.group(name="profilewatch", aliases=["pw"], pass_context=True)
    async def _profilewatch(self, ctx):
        """Monitor for flagged member name formats"""
        pass

    @_profilewatch.command(name="add")
    async def _profilewatch_add(self, ctx, name: str = "", regex: str = "", alert_level: str = "",
                   check_nick: str = "", *, reason: str = ""):
        """Add/edit member name trigger"""

        usage = "Usage: `[p]profilewatch add <name> <regex> <alert level HIGH or LOW> <check nickname YES or NO> <reason>`"
        usage += "\nNote: Name & regex fields are limited to 1 word (no spaces)."
        if (not name and not regex and not reason and not alert_level and not check_nick) or \
                (alert_level != "HIGH" and alert_level != "LOW") or (check_nick != "YES" and check_nick != "NO"):
            await ctx.send(usage)
        else:
            async with self.config.guild(ctx.guild).profilewatcher.rules() as rules:
                rules[name] = {
                    "pattern": regex,
                    "check_nick": True if check_nick == "YES" else False,
                    "alert_level": alert_level,
                    "reason": reason
                }
            await ctx.send("✅ Matcher rule successfully added!")

    @_profilewatch.command("list")
    async def _profilewatch_list(self, ctx: commands.Context):
        """List current name triggers"""
        rules = await self.config.guild(ctx.guild).profilewatcher.rules()
        pages = list(pagify("\n\n".join(WatcherCog.profile_rule_to_string(rn, r) for rn, r in rules.items())))
        base_embed_options = {"title": "Profile Watch Name Rules", "colour": await ctx.embed_colour()}
        embeds = [
            discord.Embed(**base_embed_options, description=page).set_footer(text=f"Page {index} of {len(pages)}")
            for index, page in enumerate(pages, start=1)
        ]
        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            ctx.bot.loop.create_task(
                menu(ctx=ctx, pages=embeds, controls={"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page},
                     timeout=180.0)
            )

    @_profilewatch.command("delete")
    async def _profilewatch_delete(self, ctx, name: str = ""):
        """Delete member name trigger"""

        usage = "Usage: `[p]profilewatch delete <rule name>`"
        if not name:
            await ctx.send(usage)
        else:
            async with self.config.guild(ctx.guild).profilewatcher.rules() as rules:
                if name in rules:
                    found = True
                    del rules[name]
            if found:
                await ctx.send("Rule deleted!")
            else:
                await ctx.send("Specified rule not found.")

    @_watcher.group("messagewatch", aliases=["mw"], pass_context=True)
    async def _messagewatch(self, ctx: commands.Context):
        pass

    @_messagewatch.command(name="fetchtime")
    async def _messagewatch_fetchtime(self, ctx: commands.Context, time: str):
        """Set/update the recent message fetch time (in milliseconds)."""
        try:
            val = float(time)
            await self.config.guild(ctx.guild).messagewatcher.recent_fetch_time.set(val)
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
            await self.config.guild(ctx.guild).messagewatcher.frequencies.embed.set(val)
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
            await self.config.guild(ctx.guild).messagewatcher.exemptions.member_duration.set(val)
            await ctx.send("Minimum member duration successfully updated!")
        except ValueError:
            await ctx.send("Minimum member duration FAILED to update. Please specify a `integer` value only!")

    @_messagewatch_exemptions.command(name="textmessages", aliases=["text"])
    async def _messagewatch_expemptions_textmessages(self, ctx: commands.Context, frequency: str):
        """Set/update the minimum frequency of text-only messages to be exempt."""
        try:
            val = float(frequency)
            await self.config.guild(ctx.guild).messagewatcher.exemptions.text_messages.set(val)
            await ctx.send("Text-only message frequency exemption successfully updated!")
        except ValueError:
            await ctx.send("Text-only message frequency exemption FAILED to update. Please specify a `float` value "
                           "only!")

    # Helper Functions
    @staticmethod
    def profile_rule_to_string(rule_name: str, rule) -> str:
        return f"**{rule_name}**:\nPattern: `{rule['pattern']}`\nCheck Nick: `{rule['check_nick']}`\nAlert Level: " \
               f"{rule['alert_level']}\nReason: {rule['reason']}"

    def make_voice_alert_embed(self, member: discord.Member, chan: discord.VoiceChannel) -> discord.Embed:
        """Construct the alert embed to be sent"""
        # Copied from the report Cog.
        return (
            discord.Embed(
                colour=discord.Colour.orange(),
                description="New user joined a voice channel and started streaming or enabled their camera."
            )
            .set_author(name="Suspicious User Activity", icon_url=member.avatar.url)
            .add_field(name="Server", value=member.guild.name)
            .add_field(name="User", value=member.mention)
            .add_field(name="Channel", value=chan.mention)
            .add_field(name="Timestamp", value=f"<t:{int(datetime.now().utcnow().timestamp())}:F>")
        )

    def make_profile_alert_embed(self, member: discord.Member, rule: str, matcher) -> discord.Embed:
        """Construct the alert embed to be sent"""
        # Copied from the report Cog.
        return (
            discord.Embed(
                colour=discord.Colour.red() if matcher['alert_level'] == "HIGH" else discord.Colour.orange(),
                description=escape("Rule: " + rule + "\nReason: "+matcher['reason'] or "<no message>")
            )
            .set_author(name="Profile Violation Detected", icon_url=member.avatar.url)
            .add_field(name="Server", value=member.guild.name)
            .add_field(name="Timestamp", value=f"<t:{int(datetime.now().utcnow().timestamp())}:F>")
        )

    def make_message_alert_embed(self, member: discord.Member, message: discord.Message) -> discord.Embed:
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
        filter_time = datetime.utcnow() - timedelta(milliseconds=await self.config.guild(guild).messagewatcher.recent_fetch_time())
        return [time for time in await self.get_embed_times(guild, user) if time >= filter_time]

    async def analyze_speed(self, guild: discord.Guild, trigger: discord.Message):
        """Analyzes the frequency of embeds  & attachments by a user. Should only be called upon message create/edit."""

        embed_times = await self.get_recent_embed_times(guild, trigger.author)

        # Check if we have enough basic data to calculate the frequency (prevents some config fetches below)
        if len(embed_times) < 2:
            return

        # This is a bit of a hack but check if the total embeds, regardless of times, could exceed the frequency limit
        # This is needed because one message with N > 1 embeds and no prior embed times would always trigger.
        allowable_embed_frequency = await self.config.guild(guild).messagewatcher.frequencies.embed()
        fetch_time = await self.config.guild(guild).messagewatcher.recent_fetch_time()
        if len(embed_times) < allowable_embed_frequency * fetch_time:
            return

        first_time = embed_times[0]
        last_time = embed_times[len(embed_times) - 1]
        embed_frequency = len(embed_times) / ((last_time - first_time).microseconds / 1000)  # convert to milliseconds
        if embed_frequency > allowable_embed_frequency:
            # Alert triggered, send unless exempt

            # Membership duration exemption
            allowable = trigger.author.joined_at + timedelta(
                hours=await self.config.guild(guild).messagewatcher.exemptions.member_duration())
            if datetime.now(timezone.utc) < allowable:  # Todo: this isn't supposed to exempt them, just allow exempts
                # Text-only message exemption (aka active participation exemption)
                # TODO
                return

            # No exemptions at this point, alert!
            # Credit: Taken from report Cog
            log_id = await self.config.guild(guild).logchannel()
            log = None
            if log_id:
                log = guild.get_channel(log_id)
            if not log:
                # Failed to get the channel
                return

            data = self.make_message_alert_embed(trigger.author, trigger)

            mod_pings = " ".join(
                [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
            if not mod_pings:  # If no online/idle mods
                mod_pings = " ".join([i.mention for i in log.members if not i.bot])

            await log.send(content=mod_pings, embed=data)
            # End credit

    # Listeners
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Ignore if we've already alerted on this user. Can probably find a better way.
        if member.id in self.alert_cache and self.alert_cache[member.id]:
            # Todo: Make guild-aware
            return
        else:
            self.alert_cache[member.id] = False

        if after is None or after.channel is None:  # Check if we're missing the after data or associated channel.
            return

        allowable = member.joined_at + timedelta(hours=await self.config.guild(after.channel.guild).min_joined_hours())
        if datetime.now(timezone.utc) < allowable:
            if after.self_stream or after.self_video:
                self.alert_cache[member.id] = True  # Update the cache to indicate we've alerted on this user.
                # Credit: Taken from report Cog
                log_id = await self.config.guild(after.channel.guild).logchannel()
                log = None
                if log_id:
                    log = member.guild.get_channel(log_id)
                if not log:
                    # Failed to get the channel
                    return

                data = self.make_voice_alert_embed(member, after.channel)

                # Alert level logic added
                mod_pings = " ".join(
                    [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
                if not mod_pings:  # If no online/idle mods
                    mod_pings = " ".join([i.mention for i in log.members if not i.bot])

                await log.send(content=mod_pings, embed=data)
                # End credit

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        matcher_list = await self.config.guild(member.guild).profilewatcher.rules()

        for ruleName, rule in matcher_list.items():
            hits = len(re.findall(rule['pattern'], member.name))
            if rule['check_nick'] and member.nick:
                hits += len(re.findall(rule['pattern'], member.nick))
            if hits > 0:

                # Credit: Taken from report Cog
                log_id = await self.config.guild(member.guild).logchannel()
                log = None
                if log_id:
                    log = member.guild.get_channel(log_id)
                if not log:
                    # Failed to get the channel
                    return

                data = self.make_profile_alert_embed(member, ruleName, rule)

                mod_pings = ""
                # Alert level logic added
                if rule['alert_level'] == "HIGH":
                    mod_pings = " ".join(
                        [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
                    if not mod_pings:  # If no online/idle mods
                        mod_pings = " ".join([i.mention for i in log.members if not i.bot])

                await log.send(content=mod_pings, embed=data)
                # End credit

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