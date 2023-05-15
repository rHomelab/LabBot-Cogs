"""discord red-bot overwatch profile"""
import re
from datetime import datetime
from typing import List

import discord
import discord.utils
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape, pagify
from redbot.core.utils.menus import menu, prev_page, close_menu, next_page


class OWProfileCog(commands.Cog):
    """Overwatch Profile Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384001)

        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "rules": {
                "spammer1": {  # Name of rule
                    "pattern": "^portalBlock$",  # Regex pattern to match against
                    "check_nick": False,  # Whether the user's nickname should be checked too
                    "alert_level": "HIGH",  # Severity of alerts (use: HIGH or LOW)
                    "reason": "Impostor :sus:"  # Reason for the match, used to add context to alerts
                }
            }
        }

        self.config.register_guild(**default_guild_config)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        matcher_list = await self.config.guild(member.guild).rules()

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

                data = self.make_alert_embed(member, ruleName, rule)

                mod_pings = ""
                # Alert level logic added
                if rule['alert_level'] == "HIGH":
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
    async def _add(self, ctx, name: str = "", regex: str = "", alert_level: str = "",
                   check_nick: str = "", *, reason: str = ""):
        """Add/edit member name trigger"""

        usage = "Usage: `[p]owprofile add <name> <regex> <alert level HIGH or LOW> <check nickname YES or NO> <reason>`"
        usage += "\nNote: Name & regex fields are limited to 1 word (no spaces)."
        if (not name and not regex and not reason and not alert_level and not check_nick) or \
                (alert_level != "HIGH" and alert_level != "LOW") or (check_nick != "YES" and check_nick != "NO"):
            await ctx.send(usage)
        else:
            async with self.config.guild(ctx.guild).rules() as rules:
                rules[name] = {
                    "pattern": regex,
                    "check_nick": True if check_nick == "YES" else False,
                    "alert_level": alert_level,
                    "reason": reason
                }
            await ctx.send("✅ Matcher rule successfully added!")

    @_owprofile.command("list")
    async def _list(self, ctx: commands.Context):
        """List current name triggers"""
        rules = await self.config.guild(ctx.guild).rules()
        pages = list(pagify("\n\n".join(self.rule_to_string(rn, r) for rn, r in rules)))
        base_embed_options = {"title": "Overwatch Profile Name Rules", "colour": await ctx.embed_colour()}
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
    @_owprofile.command("delete")
    async def _delete(self, ctx, name: str = ""):
        """Delete member name trigger"""

        usage = "Usage: `[p]owprofile delete <name>`"
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

    @_owprofile.command("channel")
    async def _channel(self, ctx, channel: discord.TextChannel):
        """Set the alert channel"""

        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send("Alert channel set to current channel!")

    def make_alert_embed(self, member: discord.Member, rule: str, matcher) -> discord.Embed:
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

    def rule_to_string(self, rule_name: str, rule) -> str:
        return f"{rule_name}:\n\tPattern: `{rule['pattern']}`\n\tCheck Nick: `{rule['check_nic']}`\n\tAlert Level: " \
               f"{rule['alert_level']}\n\tReason: {rule['reason']}"
