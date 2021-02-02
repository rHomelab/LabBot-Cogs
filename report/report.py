"""discord red-bot report cog"""
import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import escape


class ReportCog(commands.Cog):
    """Report Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1092901)

        default_guild_settings = {"logchannel": None}

        self.settings.register_guild(**default_guild_settings)

    @commands.group("reports")
    @commands.guild_only()
    @checks.mod()
    async def _reports(self, ctx: commands.Context):
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

    @commands.command("report")
    @commands.guild_only()
    async def cmd_report(self, ctx: commands.Context, *, message: str = None):
        """Sends a report to the mods for possible intervention

        Example:
        - `[p]report <message>`
        """
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

        report_reply = self.make_reporter_reply(ctx, message, True)
        try:
            await ctx.author.send(embed=report_reply)
        except discord.Forbidden:
            pass

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

    def make_reporter_reply(self, ctx: commands.Context, message: str, emergency: bool) -> discord.Embed:
        data = discord.Embed(color=discord.Color.red() if emergency else discord.Color.orange())
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
