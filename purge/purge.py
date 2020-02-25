"""discord red-bot purge"""
import asyncio
import discord
from redbot.core import commands, Config
from datetime import datetime, timedelta


class PurgeCog(commands.Cog):
    """Purge Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=489182828)

        default_guild_settings = {
            "purge_excludedusers": [],
            "purge_limit": 5,
            "purge_schedule": "",
            "purge_count": 0,
            "purge_lastrun": 0,
            "purge_enabled": False
        }

        self.settings.register_guild(**default_guild_settings)

        self.purge_task = self.bot.loop.create_task(
                              self.check_purgeable_users()
                          )

    def cog_unload(self):
        self.purge_task.cancel()

    async def check_purgeable_users(self):
        while self == self.bot.get_cog("PurgeCog"):
            for guild in self.bot.guilds:
                # Only run if enabled
                enabled = await self.settings.guild(guild).purge_enabled()
                if not enabled:
                    continue

                # Only run if kick_members permission is given
                if not guild.me.guild_permissions.kick_members:
                    continue

                # TODO Get and purge users
            await asyncio.sleep(60)

    async def get_purgeable_users(self, guild):
        """
        Gets users to purge.
        In addition, performs checks for excluded users.
        """
        members = []
        for member in guild.members:
            # If user has a role other than @everyone, they're safe
            roles = [role for role in member.roles
                     if guild.default_role != role]
            if len(roles) > 0:
                continue

            # If user is not older than the limit, they're safe
            timelimit = await self.settings.guild(guild).purge_limit()
            cutoff_date = datetime.utcnow() - timedelta(days=timelimit)
            if member.joined_at > cutoff_date:
                continue

            members.append(member)

        return members

    @commands.group(name="purge")
    @commands.guild_only()
    async def _purge(self, ctx: commands.Context):
        pass

    @_purge.command("execute")
    async def purge_execute(self, ctx: commands.Context):
        """Executes a purge.
        Users will be **kicked** if they haven't verified.

        Example:
        - `[p]purge execute`
        """
        pass

    @_purge.command("simulate")
    async def purge_simulate(self, ctx: commands.Context):
        """Simulates a purge.
        Users will be **detected** if they haven't verified.

        Example:
        - `[p]purge simulate`
        """
        users = await self.get_purgeable_users(ctx.guild)

        await ctx.send(f"Found {len(users)} to purge.")

    @_purge.command("exclude")
    async def purge_exclude_user(self, ctx: commands.Context):
        """Excludes an otherwise eligible user from the purge.

        Example:
        - `[p]purge exclude <user>`
        """
        pass

    @_purge.command("setlimit")
    async def purge_setlimit(self, ctx: commands.Context, limit: int):
        """Sets the number of days a user can remain in the server with no
        roles before being purged.

        Example:
        - `[p]purge setlimit <days>`
        """
        await self.settings.guild(ctx.guild).purge_limit.set(limit)
        await ctx.send(f"Set the new limit to {limit} days.")

    @_purge.command("schedule")
    async def purge_schedule(self, ctx: commands.Context):
        """Sets how often the bot should purge users.
        Accepts cron syntax. For instance `30 02 */2 * *` would be every 2
        days at 02:30.

        Example:
        - `[p]purge schedule "<cron schedule>"`
        - `[p]purge schedule "30 02 */2 * *"`
        """
        pass

    @_purge.command("enable")
    async def purge_enable(self, ctx: commands.Context):
        """Enables automated purges based on the schedule.

        Example:
        - `[p]purge enable`
        """
        await self.settings.guild(ctx.guild).purge_enabled.set(True)
        await ctx.send("Enabled the purge task.")

    @_purge.command("disable")
    async def purge_disable(self, ctx: commands.Context):
        """Disables automated purges based on the schedule.

        Example:
        - `[p]purge disable`
        """
        await self.settings.guild(ctx.guild).purge_enabled.set(False)
        await ctx.send("Disabled the purge task.")

    @_purge.command("status")
    async def purge_status(self, ctx: commands.Context):
        """Status of the bot.
        The bot will display how many users it has kicked
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]purge status`
        """
        purge_count = await self.settings.guild(ctx.guild).purge_count()
        purge_enabled = await self.settings.guild(ctx.guild).purge_enabled()

        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.add_field(name="Purged", value=f"{purge_count}")
        data.add_field(name="Enabled", value=f"{purge_enabled}")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " +
                           "send a purge status.")
