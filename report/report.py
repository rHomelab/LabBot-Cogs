"""discord red-bot report cog"""
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import escape
import discord


class ReportCog(commands.Cog):
    """Report Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1092901)

        default_guild_settings = {
            "logchannel": None
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group("reports")
    @commands.guild_only()
    @checks.mod()
    async def _reports(self, ctx: commands.Context):
        pass

    @_reports.command("logchannel")
    async def reports_logchannel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
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
    async def cmd_report(
        self,
        ctx: commands.Context,
        *,
        message: str = None
    ):
        """Sends a report to the mods for possible intervention

        Example:
        - `[p]report <message>`
        """
        # Pre-emptively delete the message for privacy reasons
        await ctx.message.delete()

        author = ctx.author
        if author.bot:
            # Ignore the bot
            return

        log_id = await self.settings.guild(ctx.guild).logchannel()
        log = None
        if log_id is not None:
            log = ctx.guild.get_channel(log_id)
        if log is None:
            # Failed to get the channel
            return

        data = discord.Embed(color=discord.Color.orange())
        data.set_author(
            name=f"Report",
            icon_url=author.avatar_url
        )
        data.add_field(name="Reporter", value=author.mention)
        data.add_field(name="Channel", value=ctx.channel.mention)
        data.add_field(name="Timestamp",
                       value=ctx.message.created_at.strftime("%Y-%m-%d %H:%I"))
        data.add_field(name="Message", value=escape(
            message or "<no message>"), inline=False)

        await log.send(embed=data)
