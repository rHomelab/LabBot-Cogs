"""discord red-bot report cog"""

import logging
from typing import Literal, TypeAlias

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape

logger = logging.getLogger("red.rhomelab.report")

# Discord character limits
EMBED_FIELD_VALUE_LIMIT = 1024
MESSAGE_BODY_LIMIT = 2000

# Maximum allowed mentions to prevent abuse
MAX_ALLOWED_MENTIONS = 100

TextLikeChannel: TypeAlias = discord.VoiceChannel | discord.StageChannel | discord.TextChannel | discord.Thread
GuildChannelOrThread: TypeAlias = "discord.guild.GuildChannel | discord.Thread"


class ReportCog(commands.Cog):
    """Report Cog"""

    bot: Red
    config: Config

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1092901)

        default_guild_settings = {
            "logchannel": None,
            "confirmations": True,
            "max_emergency_mentions": 20,
        }

        self.config.register_guild(**default_guild_settings)

    def _is_valid_channel(self, channel: "GuildChannelOrThread | None") -> TextLikeChannel | Literal[False]:
        if channel is not None and not isinstance(channel, (discord.ForumChannel, discord.CategoryChannel)):
            return channel
        return False

    @commands.group("reports")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def _reports(self, ctx: commands.Context):
        pass

    @_reports.command("logchannel")
    @commands.guild_only()
    async def reports_logchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Sets the channel to post the reports.

        Example:
        - `[p]reports logchannel <channel>`
        - `[p]reports logchannel #admin-log`
        """
        if channel.permissions_for(ctx.me).send_messages is False:
            await ctx.send("❌ I do not have permission to send messages in that channel.")
            return

        logger.debug(f"Setting log channel for guild {ctx.guild.name} ({ctx.guild.id}) to {channel.name} ({channel.id})")

        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"✅ Reports log message channel set to {channel.mention}")

    @_reports.command("confirmation")
    @commands.guild_only()
    async def reports_confirm(self, ctx: commands.GuildContext, option: bool):
        """Whether a confirmation should be sent to reporters.

        Example:
        - `[p]reports confirm <True|False>`
        """
        logger.debug(f"Setting report confirmations for guild {ctx.guild.name} ({ctx.guild.id}) to {option}")

        await self.config.guild(ctx.guild).confirmations.set(option)
        await ctx.send(f"✅ Report confirmations {'enabled' if option else 'disabled'}")

    @_reports.command("maxmentions")
    @commands.guild_only()
    async def reports_max_mentions(self, ctx: commands.GuildContext, max_mentions: int):
        """Set the maximum number of users to mention in emergency reports.

        Example:
        - `[p]reports maxmentions 15`
        - `[p]reports maxmentions 30`
        """
        if max_mentions < 1:
            await ctx.send("❌ Maximum mentions must be at least 1.")
            return
        if max_mentions > MAX_ALLOWED_MENTIONS:
            await ctx.send(f"❌ Maximum mentions cannot exceed {MAX_ALLOWED_MENTIONS}.")
            return

        logger.debug(f"Setting max emergency mentions for guild {ctx.guild.name} ({ctx.guild.id}) to {max_mentions}")

        await self.config.guild(ctx.guild).max_emergency_mentions.set(max_mentions)
        await ctx.send(f"✅ Maximum emergency mentions set to {max_mentions}")

    @_reports.command("status")
    @commands.guild_only()
    async def reports_status(self, ctx: commands.GuildContext):
        """Status of the cog."""
        reports_channel_id = await self.config.guild(ctx.guild).logchannel()
        report_confirmations = await self.config.guild(ctx.guild).confirmations()
        max_emergency_mentions = await self.config.guild(ctx.guild).max_emergency_mentions()

        if reports_channel_id:
            reports_channel = ctx.guild.get_channel(reports_channel_id)
            if reports_channel:
                reports_channel = reports_channel.mention
            else:
                reports_channel = f"Set to channel ID {reports_channel_id}, but channel could not be found!"
        else:
            reports_channel = "Unset"

        try:
            await ctx.send(
                embed=discord.Embed(colour=await ctx.embed_colour())
                .add_field(name="Reports Channel", value=reports_channel)
                .add_field(name="Report Confirmations", value=report_confirmations)
                .add_field(name="Max Emergency Mentions", value=max_emergency_mentions)
            )
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send status.")

    @commands.hybrid_command("report")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    @commands.guild_only()
    async def cmd_report(self, ctx: commands.GuildContext, *, message: str):
        """Send a report to the mods.

        Example:
        - `[p]report <message>`
        """
        logger.info(
            f"Report received from {ctx.author.name} ({ctx.author.id}) in {ctx.guild.name} "
            f"({ctx.guild.id}) #{ctx.channel.name} ({ctx.channel.id})"
        )
        logger.debug(f"Report content: {message}")
        logger.debug(f"Report content length: {len(message)} characters")
        await self.do_report(ctx.channel, ctx.message, message, False, ctx.interaction)

    @cmd_report.error
    async def on_cmd_report_error(self, ctx: commands.GuildContext, error):
        if isinstance(error, commands.CommandOnCooldown):
            logger.debug(
                f"Report command on cooldown for {ctx.author.name} ({ctx.author.id}) in guild "
                f"{ctx.guild.name} ({ctx.guild.id}), ends in {error.retry_after:.1f}s"
            )
            retry_timestamp = int(error.retry_after + ctx.message.created_at.timestamp())
            await self._send_cmd_error_response(ctx, error, f"You are on cooldown. Try again in <t:{retry_timestamp}:R>")
            return

        logger.error(f"Unexpected error occurred: {error}")
        try:
            await ctx.bot.send_to_owners(error)
        except Exception as e:
            logger.error(f"Failed to send error to owners: {e}")

    @commands.hybrid_command("emergency")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    @commands.guild_only()
    async def cmd_emergency(self, ctx: commands.GuildContext, *, message: str):
        """Pings the mods with a high-priority report.

        Example:
        - `[p]emergency <message>`
        """
        logger.info(
            f"Emergency report received from {ctx.author.name} ({ctx.author.id}) in {ctx.guild.name} "
            f"({ctx.guild.id}) #{ctx.channel.name} ({ctx.channel.id})"
        )
        logger.debug(f"Emergency report content: {message}")
        logger.debug(f"Emergency report content length: {len(message)} characters")
        await self.do_report(ctx.channel, ctx.message, message, True, ctx.interaction)

    @cmd_emergency.error
    async def on_cmd_emergency_error(self, ctx: commands.GuildContext, error):
        if isinstance(error, commands.CommandOnCooldown):
            logger.debug(
                f"Emergency command on cooldown for {ctx.author.name} ({ctx.author.id}) in guild "
                f"{ctx.guild.name} ({ctx.guild.id}), ends in {error.retry_after:.1f}s"
            )
            retry_timestamp = int(error.retry_after + ctx.message.created_at.timestamp())
            await self._send_cmd_error_response(ctx, error, f"You are on cooldown. Try again in <t:{retry_timestamp}:R>")
            return

        logger.error(f"Unexpected error occurred: {error}")
        try:
            await ctx.bot.send_to_owners(error)
        except Exception as e:
            logger.error(f"Failed to send error to owners: {e}")

    async def get_log_channel(self, guild: discord.Guild) -> TextLikeChannel | None:
        """Gets the log channel for the guild"""
        log_id = await self.config.guild(guild).logchannel()
        log = None
        if not log_id:
            logger.warning(f"No log channel set for guild {guild}")
            return

        log = guild.get_channel(log_id)
        if not log:
            # Failed to get the channel
            logger.warning(f"Failed to get log channel {log_id} in guild {guild}")
            return

        if log_channel := self._is_valid_channel(log):
            return log_channel
        else:
            logger.warning(f"Failed to get log channel {log_id}, is a invalid channel")
            return

    async def send_emergency_report(self, log_channel: TextLikeChannel, embed: discord.Embed):
        """Send emergency report, splitting across multiple messages if necessary."""
        # Get the configured maximum mentions limit
        max_mentions = await self.config.guild(log_channel.guild).max_emergency_mentions()

        # Get members from the LOG CHANNEL (where staff/mods are), not the original channel
        log_channel_members = [
            log_channel.guild.get_member(i.id) if isinstance(i, discord.ThreadMember) else i for i in log_channel.members
        ]
        logger.debug(f"Found {len(log_channel_members)} total members in log channel {log_channel.name}")

        # Get mentions for online/idle members, or all members if none online/idle
        online_idle_mentions = [
            i.mention
            for i in log_channel_members
            if i is not None and not i.bot and i.status in [discord.Status.online, discord.Status.idle]
        ]
        all_mentions = [i.mention for i in log_channel_members if i is not None and not i.bot]

        logger.debug(f"Found {len(online_idle_mentions)} online/idle members, {len(all_mentions)} total non-bot members")

        mentions_to_use = online_idle_mentions or all_mentions

        # Limit the number of mentions to the configured maximum
        if len(mentions_to_use) > max_mentions:
            mentions_to_use = mentions_to_use[:max_mentions]
            logger.info(f"Limited mentions to configured maximum of {max_mentions}")

        if not mentions_to_use:
            logger.warning(f"Could not find any members to mention in emergency report for guild {log_channel.guild.name}")
            # No mentions to send, just send the embed
            await log_channel.send(embed=embed)
            return

        # Split mentions into chunks that fit within Discord's character limit
        mention_chunks = []
        current_chunk = ""

        for mention in mentions_to_use:
            test_chunk = f"{current_chunk} {mention}".strip()
            if len(test_chunk) > MESSAGE_BODY_LIMIT:
                # Current chunk is full, start a new one
                if current_chunk:
                    mention_chunks.append(current_chunk)
                current_chunk = mention
            else:
                current_chunk = test_chunk

        # Add the last chunk if it has content
        if current_chunk:
            mention_chunks.append(current_chunk)

        # Send message(s)
        for idx, chunk in enumerate(mention_chunks):
            if idx == 0:
                # Send the first message with the embed and first chunk of mentions
                logger.debug(f"Sending emergency report with embed and {len(chunk)} character mention block")
                await log_channel.send(content=chunk, embed=embed)
            else:
                logger.debug(f"Sending additional mention block {idx + 1}/{len(mention_chunks)} ({len(chunk)} characters)")
                await log_channel.send(content=chunk)

    async def do_report(
        self,
        channel: "discord.guild.GuildChannel | discord.Thread",
        message: discord.Message,
        report_body: str,
        emergency: bool,
        interaction: discord.Interaction | None,
    ):
        """Sends a report to the mods for possible intervention"""
        report_type = "emergency" if emergency else "regular"
        logger.debug(f"Processing {report_type} report from {message.author.name} ({message.author.id})")

        # Pre-emptively delete the message for privacy reasons
        if interaction is None:
            logger.debug("Deleting original report message for privacy")
            await message.delete()

        # Check if report body needs truncation
        original_length = len(report_body)
        if was_truncated := len(report_body) > EMBED_FIELD_VALUE_LIMIT:
            report_body = report_body[:EMBED_FIELD_VALUE_LIMIT]
            logger.info(f"Report content truncated from {original_length} to {len(report_body)} characters")

        log_channel = await self.get_log_channel(channel.guild)
        if log_channel is None:
            logger.warning(f"No log channel configured for guild {channel.guild.name} ({channel.guild.id})")
            await self.notify_guild_owner_config_error(channel, message, report_body)
            return

        embed = await self.make_report_embed(channel, message, report_body, emergency)

        logger.info(f"Sending {report_type} report to log channel {log_channel.name} ({log_channel.id})")
        if isinstance(channel, TextLikeChannel) and emergency:
            await self.send_emergency_report(log_channel, embed)
        else:
            # Not an emergency or not a text-like channel (maybe can't retrieve members), just send the embed
            await log_channel.send(embed=embed)

        # Notify user if their report was truncated
        if was_truncated:
            logger.debug("Notifying user about report truncation")
            await self.notify_truncation(message, interaction, original_length, len(report_body))

        # Construct the report reply embed
        report_reply = self.make_reporter_reply(channel.guild, channel, report_body, emergency)

        # Send interaction response if this is a slash command
        if interaction is not None and not interaction.response.is_done():
            logger.debug("Sending confirmation via interaction response")
            await interaction.response.send_message(embed=report_reply, ephemeral=True)

        # Else send a DM if DM confirmations are enabled
        elif self.config.guild(channel.guild).confirmations():
            logger.debug("Sending confirmation via DM")
            try:
                await message.author.send(embed=report_reply)
            except discord.Forbidden as exc:
                logger.warning(
                    f"Failed to send report confirmation to {message.author.global_name} ({message.author.id}): {exc}"
                )

    async def make_report_embed(
        self, channel: GuildChannelOrThread, message: discord.Message, report_body: str, emergency: bool
    ) -> discord.Embed:
        embed = (
            discord.Embed(
                colour=discord.Colour.red() if emergency else discord.Colour.orange(),
            )
            .set_author(name="Report", icon_url=message.author.display_avatar.url)
            .add_field(name="Reporter", value=message.author.mention)
            .add_field(name="Timestamp", value=discord.utils.format_dt(message.created_at, "F"))
        )

        if isinstance(channel, TextLikeChannel):
            last_msg = [msg async for msg in channel.history(limit=1, before=message.created_at)][0]  # noqa: RUF015
            embed.add_field(name="Context Region", value=last_msg.jump_url if last_msg else "No messages found")
        else:
            embed.add_field(name="Channel", value=message.channel.mention)  # type: ignore

        embed.add_field(name="Report Content", value=escape(report_body or "<no message>"))
        return embed

    def make_reporter_reply(
        self, guild: discord.Guild, channel: GuildChannelOrThread, report_body: str, emergency: bool
    ) -> discord.Embed:
        """Construct the reply embed to be sent"""
        guild_icon = guild.icon
        return (
            discord.Embed(
                colour=discord.Colour.red() if emergency else discord.Colour.orange(),
            )
            .set_author(name="Report Received", icon_url=guild_icon.url if guild_icon else None)
            .add_field(name="Report Origin", value=channel.mention)
            .add_field(name="Report Content", value=escape(report_body or "<no message>"))
        )

    async def notify_truncation(
        self, message: discord.Message, interaction: discord.Interaction | None, original_length: int, truncated_length: int
    ):
        """Notify user that their report was truncated."""
        logger.debug(f"Notifying {message.author.name} ({message.author.id}) about report truncation")
        try:
            truncation_msg = (
                f"⚠️ Your report was truncated from {original_length} to {truncated_length} characters "
                f"due to Discord's limits. The report was still sent successfully."
            )
            if interaction is not None and not interaction.response.is_done():
                await interaction.followup.send(truncation_msg, ephemeral=True)
                logger.debug("Truncation notification sent via interaction followup message")
            else:
                await message.author.send(truncation_msg)
                logger.debug("Truncation notification sent via DM")
        except discord.Forbidden as exc:
            logger.error(f"Failed to notify {message.author.global_name} ({message.author.id}) about report truncation: {exc}")

    async def notify_guild_owner_config_error(
        self, channel: "discord.guild.GuildChannel | discord.Thread", message: discord.Message, report_body: str
    ):
        """Notify guild owner about misconfigured report log channel."""
        if channel.guild.owner is None:
            logger.warning(
                f"Can't find an owner of guild {channel.guild.name} ({channel.guild.id}) to notify about config error"
            )
            return

        logger.info(f"Notifying guild owner about misconfigured reports for guild {channel.guild.name} ({channel.guild.id})")

        base_msg = (
            f"⚠️ User {message.author.mention} attempted to make a report in {channel.jump_url}, "
            + "but the cog is misconfigured. Please check the logs."
        )

        # Add report body if it fits within Discord's 2000 char limit
        if report_body:
            report_addition = f"\nUser report: {report_body}"
            if len(base_msg + report_addition) <= MESSAGE_BODY_LIMIT:
                base_msg += report_addition
            else:
                # Truncate report to fit
                max_report_length = MESSAGE_BODY_LIMIT - len(base_msg) - len("\nUser report: ...")
                if max_report_length > 0:
                    truncated = report_body[:max_report_length]
                    base_msg += f"\nUser report: {truncated}..."
                    logger.debug(f"Truncated report body for guild owner notification ({len(truncated)} chars)")

        try:
            await channel.guild.owner.send(base_msg)
            logger.info("Successfully notified guild owner about config error")
        except discord.Forbidden:
            logger.error("Failed to send config error notification to guild owner - no DM permissions")

    async def _send_cmd_error_response(self, ctx: commands.GuildContext, error, response: str):
        """
        Sends a command error response to the user.

        If the context has an unresponded interaction, sends an ephemeral error message.
        Otherwise, deletes the original message and sends the response directly to the user.

        Parameters:
            ctx (commands.GuildContext): The command context containing guild information
            error: The error object to be sent as a message
            response (str): The response message to send to the user
        Returns:
            None
        """
        if ctx.interaction is not None and not ctx.interaction.response.is_done():
            await ctx.interaction.response.send_message(str(error), ephemeral=True)
        else:
            await ctx.message.delete()
            await ctx.author.send(response)
