"""discord red-bot overwatch profile"""
import re
from datetime import datetime

import discord
import discord.utils
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape


class OWProfileCog(commands.Cog):
    """Overwatch Profile Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384001)

        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "matchers": {
                "spammer1": {  # Name of rule
                    "pattern": "",  # Regex pattern to match against
                    "check_nick": False,  # Whether the user's nickname should be checked too
                    "alert_level": "",  # Severity of alerts (use: HIGH or LOW)
                    "reason": ""  # Reason for the match, used to add context to alerts
                }
            }
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        matcher_list = await self.config.guild(member.guild).matchers()

        for rule, matcher in matcher_list.items():
            hits = len(re.findall(matcher.pattern(), member.name))
            if matcher.check_nick():
                hits += len(re.findall(matcher.pattern(), member.nick))
            if hits > 0:

                # Credit: Taken from report Cog
                log_id = await self.config.guild(member.guild).logchannel()
                log = None
                if log_id:
                    log = member.guild.get_channel(log_id)
                if not log:
                    # Failed to get the channel
                    return

                data = self.make_alert_embed(member, rule, matcher)

                mod_pings = ""
                # Alert level logic added
                if matcher.alert_level() == "HIGH":
                    mod_pings = " ".join(
                        [i.mention for i in log.members if not i.bot and str(i.status) in ["online", "idle"]])
                    if not mod_pings:  # If no online/idle mods
                        mod_pings = " ".join([i.mention for i in log.members if not i.bot])

                await log.send(content=mod_pings, embed=data)
                # End credit

    # Command groups

    @checks.admin()
    @commands.group(name="owprofile", pass_context=True)
    async def _owprofile(self, ctx):
        """Monitor for flagged member name formats"""

    # Commands

    @_owprofile.command(name="add")
    async def _add(self, ctx, name: str = "", regex: str = "", reason: str = "", alert_level: str = "", check_nick: str = ""):
        """Add member name trigger"""

        usage = "Usage: `[p]owprofile add <name> <regex> <reason> <alert level HIGH or LOW> <check nickname YES or NO>"
        if (not name and not regex and not reason and not alert_level and not check_nick) or \
                (alert_level != "HIGH" and alert_level != "LOW") or (check_nick != "YES" and check_nick != "NO"):
            await ctx.send(usage)
        else:
            async with self.config.guild(ctx.guild).matchers() as matchers:
                matchers[name] = {
                    "pattern": regex,
                    "check_nick": True if check_nick == "YES" else False,
                    "alert_level": alert_level,
                    "reason": reason
                }
            await ctx.send("✅ Matcher rule successfully added!")

    @_owprofile.command("delete")
    async def _delete(self, ctx, name: str = ""):
        """Delete member name trigger"""

        usage = "Usage: [p]owprofile delete <name>"
        if not name:
            await ctx.send(usage)
        else:
            async with self.config.guild(ctx.guild).matchers() as matchers:
                if name in matchers:
                    found = True
                    del matchers[name]
            if found:
                await ctx.send("Matcher rule deleted!")
            else:
                await ctx.send("Specified matcher rule not found.")

    def make_alert_embed(self, member: discord.Member, rule: str, matcher) -> discord.Embed:
        """Construct the alert embed to be sent"""
        # Copied from the report Cog.
        return (
            discord.Embed(
                colour=discord.Colour.red() if matcher.alert_level() == "HIGH" else discord.Colour.orange(),
                description=escape("Rule: " + rule + "\nReason: "+matcher.reason() or "<no message>")
            )
            .set_author(name="Profile Violation Detected", icon_url=member.avatar.url)
            .add_field(name="Server", value=member.guild.name)
            .add_field(name="Timestamp", value=f"<t:{int(datetime.now().utcnow().timestamp())}:F>")
        )
