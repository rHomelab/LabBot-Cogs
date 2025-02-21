"""discord red-bot report cog"""

import logging
from typing import Literal, TypeAlias

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape

logger = logging.getLogger("red.rhomelab.report")

TextLikeChannnel: TypeAlias = discord.VoiceChannel | discord.StageChannel | discord.TextChannel | discord.Thread
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
        }

        self.config.register_guild(**default_guild_settings)

    def _is_valid_channel(self, channel: "GuildChannelOrThread | None") -> TextLikeChannnel | Literal[False]:
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
        """Sets the channel to post the reports

        Example:
        - `[p]reports logchannel <channel>`
        - `[p]reports logchannel #admin-log`
        """
        if channel.permissions_for(ctx.me).send_messages is False:
            await ctx.send("❌ I do not have permission to send messages in that channel.")
            return
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"✅ Reports log message channel set to {channel.mention}")

    @_reports.command("confirm")
    @commands.guild_only()
    async def reports_confirm(self, ctx: commands.GuildContext, option: str):
        """Whether a confirmation should be sent to reporters.

        Example:
        - `[p]reports confirm <True|False>`
        """
        try:
            confirmation = strtobool(option)
        except ValueError:
            await ctx.send("❌ Invalid option. Use: `[p]reports confirm <True|False>`")
            return
        await self.config.guild(ctx.guild).confirmations.set(confirmation)
        await ctx.send(f"✅ Report confirmations {'enabled' if confirmation else 'disabled'}")

    @commands.hybrid_command("report")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    @commands.guild_only()
    async def cmd_report(self, ctx: commands.GuildContext, *, message: str):
        """Send a report to the mods.

        Example:
        - `[p]report <message>`
        """
        await self.do_report(ctx.channel, ctx.message, message, False, ctx.interaction)

    @cmd_report.error
    async def on_cmd_report_error(self, ctx: commands.GuildContext, error):
        if isinstance(error, commands.CommandOnCooldown):
            if ctx.interaction is not None:
                await ctx.interaction.response.send_message(str(error), ephemeral=True)
            else:
                await ctx.message.delete()
                await ctx.author.send(f"You are on cooldown. Try again in <t:{error.retry_after}:R>")

    @commands.hybrid_command("emergency")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    @commands.guild_only()
    async def cmd_emergency(self, ctx: commands.GuildContext, *, message: str):
        """Pings the mods with a high-priority report.

        Example:
        - `[p]emergency <message>`
        """
        await self.do_report(ctx.channel, ctx.message, message, True, ctx.interaction)

    @cmd_report.error
    async def on_cmd_emergency_error(self, ctx: commands.GuildContext, error):
        if isinstance(error, commands.CommandOnCooldown):
            if ctx.interaction is not None:
                await ctx.interaction.response.send_message(str(error), ephemeral=True)
            else:
                await ctx.message.delete()
                await ctx.author.send(f"You are on cooldown. Try again in <t:{error.retry_after}:R>")

    async def get_log_channel(self, guild: discord.Guild) -> TextLikeChannnel | None:
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

    async def do_report(
        self,
        channel: "discord.guild.GuildChannel | discord.Thread",
        message: discord.Message,
        report_body: str,
        emergency: bool,
        interaction: discord.Interaction | None,
    ):
        """Sends a report to the mods for possible intervention"""
        # Pre-emptively delete the message for privacy reasons
        if interaction is None:
            await message.delete()

        log_channel = await self.get_log_channel(channel.guild)
        if log_channel is None:
            if channel.guild.owner is not None:
                report_msg = f"\nUser report: {report_body}" if report_body else ""
                await channel.guild.owner.send(
                    f"⚠️ User {message.author.mention} attempted to make a report in {channel.jump_url}, "
                    + "but the cog is misconfigured. Please check the logs."
                    + report_msg
                )
            return

        embed = await self.make_report_embed(channel, message, report_body, emergency)
        msg_body = None
        if isinstance(channel, TextLikeChannnel):
            # Ping online and idle mods or all mods if none with such a status are found.
            if emergency:
                channel_members = [
                    channel.guild.get_member(i.id) if isinstance(i, discord.ThreadMember) else i for i in channel.members
                ]
                msg_body = " ".join(
                    [
                        i.mention
                        for i in channel_members
                        if i is not None and not i.bot and i.status in [discord.Status.online, discord.Status.idle]
                    ]
                    or [i.mention for i in channel_members if i is not None and not i.bot]
                )

        await log_channel.send(content=msg_body, embed=embed)

        confirm = await self.config.guild(channel.guild).confirmations()
        if confirm:
            report_reply = self.make_reporter_reply(channel.guild, channel, report_body, emergency)
            try:
                if interaction is not None:
                    await interaction.response.send_message(embed=report_reply, ephemeral=True)
                else:
                    await message.author.send(embed=report_reply)
            except discord.Forbidden:
                logger.warning(f"Failed to send report confirmation to {message.author.global_name} ({message.author.id})")
                pass

    async def make_report_embed(
        self, channel: GuildChannelOrThread, message: discord.Message, report_body: str, emergency: bool
    ) -> discord.Embed:
        embed = (
            discord.Embed(
                colour=discord.Colour.red() if emergency else discord.Colour.orange(),
            )
            .set_author(name="Report", icon_url=message.author.display_avatar.url)
            .add_field(name="Reporter", value=message.author.mention)
            .add_field(name="Timestamp", value=f"<t:{int(message.created_at.timestamp())}:F>")
        )

        if isinstance(channel, TextLikeChannnel):
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


def strtobool(value: str) -> bool:
    value = value.lower()
    if value in ("y", "yes", "on", "1", "true", "t"):
        return True
    return False
