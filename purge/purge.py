"""discord red-bot purge"""

import asyncio
from datetime import datetime, timedelta

import discord
from croniter import croniter
from croniter.croniter import CroniterError
from redbot.core import Config, checks, commands


class PurgeCog(commands.Cog):
    """Purge Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=489182828)

        default_guild_settings = {
            "excludedusers": [],
            "minage": 5,
            "schedule": "0 */6 * * *",
            "count": 0,
            "lastrun": None,
            "enabled": False,
            "logchannel": None,
        }

        self.config.register_guild(**default_guild_settings)

        self.purge_task = self.bot.loop.create_task(self.check_purgeable_users())

    async def cog_unload(self):
        self.purge_task.cancel()

    async def set_crontab(self, guild, crontab):
        try:
            croniter(crontab)
            await self.config.guild(guild).schedule.set(crontab)
            return crontab
        except CroniterError:
            return False

    async def check_purgeable_users(self):
        while self == self.bot.get_cog("PurgeCog"):
            for guild in self.bot.guilds:
                # Only run if enabled
                enabled = await self.config.guild(guild).enabled()
                if not enabled:
                    continue

                # Is it time to run?
                cur_epoch = datetime.utcnow()
                last_run = await self.config.guild(guild).lastrun()
                last_run = last_run or 0
                crontab = await self.config.guild(guild).schedule()
                cron_check = croniter(crontab, last_run)
                next_execution_date = cron_check.get_next(datetime)

                if next_execution_date > cur_epoch:
                    # It's not scheduled to run yet
                    continue

                # Set the last run
                await self.config.guild(guild).lastrun.set(cur_epoch.timestamp())

                # Only run if kick_members permission is given
                if not guild.me.guild_permissions.kick_members:
                    continue

                channel = await self.config.guild(guild).logchannel()
                output = guild.get_channel(channel)
                if output is None:
                    # The log channel no longer exists
                    continue

                data = await self._purge_users(guild, "Scheduled")

                if not data:
                    # No users purged
                    continue

                try:
                    await output.send(embed=data)
                except discord.Forbidden:
                    await output.send("I need the `Embed links` permission " + "to send a purge board.")

            await asyncio.sleep(60)

    async def _purge_users(self, guild: discord.Guild, title: str):
        users = await self.get_purgeable_users(guild)

        if len(users) == 0:
            return None

        users_kicked = ""

        for user in users:
            result = await self._purge_user(user)
            if not result:
                pass
            new_list = users_kicked + "\n" + await self._get_safe_username(user)
            if len(new_list) > 2048:  # noqa: PLR2004
                break
            users_kicked = new_list

        data = discord.Embed(colour=discord.Colour.orange(), timestamp=datetime.utcnow())
        data.title = f"{title} Purge - Purged {len(users)}"
        data.description = users_kicked

        return data

    async def _get_safe_username(self, user: discord.Member):
        replaced_name = user.name.replace("`", "")
        return f"{replaced_name}#{user.discriminator} ({user.id})"

    async def _purge_user(self, user: discord.Member):
        try:
            # Kick the user from the server and log it
            await user.kick()

            count = await self.config.guild(user.guild).count()
            count += 1
            await self.config.guild(user.guild).count.set(count)

            return True
        except (discord.HTTPException, discord.Forbidden):
            return False

    async def get_purgeable_users(self, guild):
        """
        Gets users to purge.
        In addition, performs checks for excluded users.
        """
        members = []
        for member in guild.members:
            # If user has a role other than @everyone, they're safe
            roles = [role for role in member.roles if guild.default_role != role]
            if len(roles) > 0:
                continue

            # If user is not older than the minimum age, they're safe
            timelimit = await self.config.guild(guild).minage()
            cutoff_date = datetime.utcnow() - timedelta(days=timelimit)
            if member.joined_at > cutoff_date:
                continue

            async with self.config.guild(guild).excludedusers() as excluded_users:
                # If user is excluded from the purge, they're safe
                if member and member.id in excluded_users:
                    continue

            members.append(member)

        return members

    @commands.group(name="purge")  # type: ignore
    @commands.guild_only()
    @checks.mod()
    async def _purge(self, ctx: commands.Context):
        pass

    @_purge.command("logchannel")
    async def purge_logchannel(self, ctx: commands.GuildContext, channel: discord.TextChannel):
        """Logs details of purging to this channel.
        The bot must have permission to write to this channel.

        Example:
        - `[p]purge logchannel #<channel>`
        """
        await self.config.guild(ctx.guild).logchannel.set(channel.id)
        await ctx.send("Purge log channel set.")

    @_purge.command("execute")
    async def purge_execute(self, ctx: commands.GuildContext):
        """Executes a purge.
        Users will be **kicked** if they haven't verified.

        Example:
        - `[p]purge execute`
        """
        data = await self._purge_users(ctx.guild, "Manual")

        if data is None:
            await ctx.send("No users to purge.")
            return

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send " + "a purge board.")

    @_purge.command("simulate")
    async def purge_simulate(self, ctx: commands.GuildContext):
        """Simulates a purge.
        Users will be **detected** if they haven't verified.

        Example:
        - `[p]purge simulate`
        """
        users = await self.get_purgeable_users(ctx.guild)

        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.title = f"Purge Simulation - Found {len(users)}"
        data.description = ""

        for user in users:
            new_desc = data.description + "\n" + await self._get_safe_username(user)
            if len(new_desc) > 2048:  # noqa: PLR2004
                break
            data.description = new_desc

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " + "send a purge simulation board.")

    @_purge.command("exclude")
    async def purge_exclude_user(self, ctx: commands.GuildContext, user: discord.Member):
        """Excludes an otherwise eligible user from the purge.

        Example:
        - `[p]purge exclude <user>`
        """
        guild = ctx.guild
        added = False
        # Get excluded users list
        async with self.config.guild(guild).excludedusers() as excluded_users:
            if user and user.id not in excluded_users:
                excluded_users.append(user.id)
                added = True

        if added:
            await ctx.send("That user is now safe from pruning!")
        else:
            await ctx.send("That user is already safe from pruning!")

    @_purge.command("include")
    async def purge_include_user(self, ctx: commands.GuildContext, user: discord.Member):
        """Includes a possibly-eligible user in the purge checks.

        Example:
        - `[p]purge include <user>`
        """
        guild = ctx.guild
        removed = False
        # Get excluded users list
        async with self.config.guild(guild).excludedusers() as excluded_users:
            if user and user.id in excluded_users:
                excluded_users.remove(user.id)
                removed = True

        if removed:
            await ctx.send("That user is no longer safe from pruning!")
        else:
            await ctx.send("That user is already not safe from pruning!")

    @_purge.command("minage")
    async def purge_minage(self, ctx: commands.GuildContext, minage: int):
        """Sets the number of days a user can remain in the server with no
        roles before being purged.

        Example:
        - `[p]purge minage <days>`
        """
        if minage < 0:
            await ctx.send("Cannot set the minimum age to 0 days or less")

        await self.config.guild(ctx.guild).minage.set(minage)
        await ctx.send(f"Set the new minimum age to {minage} days.")

    @_purge.command("schedule")
    async def purge_schedule(self, ctx: commands.GuildContext, schedule: str):
        """Sets how often the bot should purge users.
        Accepts cron syntax. For instance `30 02 */2 * *` would be every 2
        days at 02:30.

        Example:
        - `[p]purge schedule "<cron schedule>"`
        - `[p]purge schedule "30 02 */2 * *"`
        """
        new_shedule = await self.set_crontab(ctx.guild, schedule)
        if not new_shedule:
            await ctx.send("The schedule given was invalid.")
        else:
            await ctx.send(f"Set the schedule to `{new_shedule}`.")

    @_purge.command("enable")
    async def purge_enable(self, ctx: commands.GuildContext):
        """Enables automated purges based on the schedule.

        Example:
        - `[p]purge enable`
        """
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send("Enabled the purge task.")

    @_purge.command("disable")
    async def purge_disable(self, ctx: commands.GuildContext):
        """Disables automated purges based on the schedule.

        Example:
        - `[p]purge disable`
        """
        await self.config.guild(ctx.guild).enabled.set(False)
        await ctx.send("Disabled the purge task.")

    @_purge.command("status")
    async def purge_status(self, ctx: commands.GuildContext):
        """Status of the bot.
        The bot will display how many users it has kicked
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]purge status`
        """
        purge_count = await self.config.guild(ctx.guild).count()
        purge_enabled = await self.config.guild(ctx.guild).enabled()
        purge_minage = await self.config.guild(ctx.guild).minage()
        purge_last_run = await self.config.guild(ctx.guild).lastrun()
        purge_schedule = await self.config.guild(ctx.guild).schedule()
        purge_log = await self.config.guild(ctx.guild).logchannel()

        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.add_field(name="Purged", value=f"{purge_count} users")
        data.add_field(name="Enabled", value=f"{purge_enabled}")
        data.add_field(name="Min Age", value=f"{purge_minage} days")
        if purge_log is None:
            purge_log = "Not set"
        else:
            logchannel = ctx.guild.get_channel(purge_log)
            if logchannel is None:
                purge_log = "Not set"
            else:
                purge_log = f"#{logchannel.name}"

        data.add_field(name="Log Channel", value=purge_log)

        last_run_friendly = "Never"
        if purge_last_run is not None:
            last_run = datetime.utcfromtimestamp(purge_last_run)
            last_run_friendly = last_run.strftime("%Y-%m-%d %H:%M:%SZ")
        data.add_field(name="Last Run", value=f"{last_run_friendly}")

        if (purge_last_run is not None or purge_enabled) and purge_schedule is not None:
            next_date = croniter(purge_schedule, purge_last_run or datetime.utcnow()).get_next(datetime)
            next_run_friendly = next_date.strftime("%Y-%m-%d %H:%M:%SZ")

            data.add_field(name="Next Run", value=f"{next_run_friendly}")

        if purge_schedule is not None:
            data.add_field(name="Schedule", value=f"`{purge_schedule}`")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " + "send a purge status.")
