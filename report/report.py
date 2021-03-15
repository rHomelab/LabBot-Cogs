"""discord red-bot report cog"""
from distutils.util import strtobool

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import escape


class ReportCog(commands.Cog):
    """Report Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1092901)

        default_guild_settings = {
            "logchannel": None,
            "confirmations": True,
            # {"id": str, "emergencies": bool, "reports": bool} both bools default to True
            "channels": [],
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group("reports")
    @commands.guild_only()
    @checks.mod()
    async def _reports(self, ctx: commands.Context):
        pass

    @commands.group("emergencies")
    @commands.guild_only()
    @checks.mod()
    async def _emergencies(self, ctx: commands.Context):
        pass

    @_reports.command("logchannel")
    async def reports_logchannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Sets the channel to post the reports

        Example:
        - `[p]reports logchannel <channel>`
        - `[p]reports logchannel #admin-log`
        """
        await self.settings.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send(f"Reports log message channel set to `{channel.name}`")

    @_reports.command("confirm")
    async def reports_confirm(self, ctx: commands.Context, option: str):
        """Changes if confirmations should be sent to reporters upon a report/emergency.

        Example:
        - `[p]reports confirm <True|False>`
        """
        try:
            option = bool(strtobool(option))
        except ValueError:
            await ctx.send("Invalid option. Use: `[p]reports confirm <True|False>`")
            return
        await self.settings.guild(ctx.guild).confirmations.set(option)
        await ctx.send(f"Send report confirmations: `{option}`")

    @commands.command("report")
    @commands.guild_only()
    async def cmd_report(self, ctx: commands.Context, *, message: str = None):
        """Sends a report to the mods for possible intervention

        Example:
        - `[p]report <message>`
        """
        pre_check = await self.enabled_channel_check(ctx, "reports")
        if not pre_check:
            return

        # Pre-emptively delete the message for privacy reasons
        await ctx.message.delete()

        log_id = await self.settings.guild(ctx.guild).logchannel()
        log = None
        if log_id:
            log = ctx.guild.get_channel(log_id)
        if not log:
            # Failed to get the channel
            return

        data = self.make_report_embed(ctx, message)
        await log.send(embed=data)

        confirm = await self.settings.guild(ctx.guild).confirmations()
        if confirm:
            report_reply = self.make_reporter_reply(ctx, message, False)
            try:
                await ctx.author.send(embed=report_reply)
            except discord.Forbidden:
                pass

    @commands.command("emergency")
    @commands.guild_only()
    async def cmd_emergency(self, ctx: commands.Context, *, message: str = None):
        """Pings the mods with a report for possible intervention

        Example:
        - `[p]emergency <message>`
        """
        pre_check = await self.enabled_channel_check(ctx, "emergencies")
        if not pre_check:
            return

        # Pre-emptively delete the message for privacy reasons
        await ctx.message.delete()

        log_id = await self.settings.guild(ctx.guild).logchannel()
        log = None
        if log_id:
            log = ctx.guild.get_channel(log_id)
        if not log:
            # Failed to get the channel
            return

        data = self.make_report_embed(ctx, message)
        mod_pings = " ".join(
            [
                i.mention
                for i in log.members
                if not i.bot and str(i.status) in ["online", "idle"]
            ]
        )
        if not mod_pings:  # If no online/idle mods
            mod_pings = " ".join([i.mention for i in log.members if not i.bot])
        await log.send(content=mod_pings, embed=data)

        confirm = await self.settings.guild(ctx.guild).confirmations()
        if confirm:
            report_reply = self.make_reporter_reply(ctx, message, True)
            try:
                await ctx.author.send(embed=report_reply)
            except discord.Forbidden:
                pass

    @_reports.command("channel")
    async def reports_channel(
        self, ctx: commands.Context, rule: str, channel: discord.TextChannel
    ):
        """Allows/denies the use of reports in specific channels

        Example:
        - `[p]reports channel <allow|deny> <channel>`
        - `[p]reports channel deny #general
        """
        supported_rules = ("deny", "allow")
        if rule.lower() not in supported_rules:
            await ctx.send("Rule argument must be `allow` or `deny`")
            return

        bool_conversion = bool(supported_rules.index(rule.lower()))

        async with self.settings.guild(ctx.guild).channels() as channels:
            data = filter(lambda c: c["id"] == str(ctx.channel.id), channels)
            if data:
                next(data)["reports"] = bool_conversion
            else:
                channels.append(
                    {
                        "id": str(ctx.channel.id),
                        "reports": bool_conversion,
                        "emergencies": True,
                    }
                )

        await ctx.send(
            "Reports {} in {}".format(
                "allowed" if bool_conversion else "denied", channel.mention
            )
        )

    @_emergencies.command("channel")
    async def emergencies_channel(
        self, ctx: commands.Context, rule: str, channel: discord.TextChannel
    ):
        """Allows/denies the use of emergencies in specific channels

        Example:
        - `[p]emergencies channel <allow|deny> <channel>`
        - `[p]emergencies channel deny #general
        """
        supported_rules = ("deny", "allow")
        if rule.lower() not in supported_rules:
            await ctx.send("Rule argument must be `allow` or `deny`")
            return

        bool_conversion = bool(supported_rules.index(rule.lower()))

        async with self.settings.guild(ctx.guild).channels() as channels:
            data = filter(lambda c: c["id"] == str(ctx.channel.id), channels)
            if data:
                next(data)["emergencies"] = bool_conversion
            else:
                channels.append(
                    {
                        "id": str(ctx.channel.id),
                        "reports": True,
                        "emergencies": bool_conversion,
                    }
                )

        await ctx.send(
            "Emergencies {} in {}".format(
                "allowed" if bool_conversion else "denied", channel.mention
            )
        )

    async def enabled_channel_check(
        self, ctx: commands.Context, invoking_cmd: str
    ) -> bool:
        """Checks that reports/emergency commands are enabled in the current channel"""
        async with self.settings.guild(ctx.guild).channels() as channels:
            channel = filter(lambda c: c["id"] == str(
                ctx.channel.id), channels)

            if channel:
                return next(channel)[invoking_cmd]

            # Insert an entry for this channel if it doesn't exist
            channels.append({
                "id": str(ctx.channel.id),
                "emergencies": True,
                "reports": True
            })
            return True

    def make_report_embed(self, ctx: commands.Context, message: str):
        """Construct the embed to be sent"""
        data = discord.Embed(color=discord.Color.orange())
        data.set_author(name="Report", icon_url=ctx.author.avatar_url)
        data.add_field(name="Reporter", value=ctx.author.mention)
        data.add_field(name="Channel", value=ctx.channel.mention)
        data.add_field(
            name="Timestamp", value=ctx.message.created_at.strftime("%Y-%m-%d %H:%I")
        )
        data.add_field(
            name="Message", value=escape(message or "<no message>"), inline=False
        )
        return data

    def make_reporter_reply(
        self, ctx: commands.Context, message: str, emergency: bool
    ) -> discord.Embed:
        """Construct the reply embed to be sent"""
        data = discord.Embed(
            color=discord.Color.red() if emergency else discord.Color.orange()
        )
        data.set_author(name="Report Received", icon_url=ctx.author.avatar_url)
        data.add_field(name="Server", value=ctx.guild.name)
        data.add_field(name="Channel", value=ctx.channel.mention)
        data.add_field(
            name="Timestamp", value=ctx.message.created_at.strftime("%Y-%m-%d %H:%I")
        )
        data.add_field(
            name="Message", value=escape(message or "<no message>"), inline=False
        )
        return data
