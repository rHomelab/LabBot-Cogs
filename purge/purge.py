"""discord red-bot purge"""
from datetime import datetime, timedelta
from typing import List

import discord
from discord.ext import tasks
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify

from .utils import ConfigHelper


def _get_safe_username(member: discord.Member):
    return f"{member.display_name}#{member.discriminator}".replace("`", "")


class PurgeCog(commands.Cog):
    """Purge Cog"""

    bot: Red
    config: ConfigHelper

    def __init__(self, bot: Red):
        self.bot = bot
        self.purge_task.start()

    def cog_unload(self):
        self.purge_task.cancel()

    @tasks.loop(minutes=1.0)
    async def purge_task(self):
        for guild in self.bot.guilds:
            if not await self.config.should_run(guild):
                continue

            await self.config.set_last_run(guild)
            log_channel = await self.config.get_log_channel(guild)
            log_embeds = await self._purge_users(guild, "Scheduled")

            if not log_embeds:
                # No users purged
                continue

            if not log_channel.permissions_for(guild.me).embed_links:
                await log_channel.send("I need the `Embed links` permission to send a purge board.")
                continue

            if not log_channel.permissions_for(guild.me).send_messages:
                # Can't send messages to the log channel
                continue

            for embed in log_embeds:
                await log_channel.send(embed=embed)

    async def _purge_users(self, guild: discord.Guild, execution_mode: str) -> List[discord.Embed]:
        members = await self.get_purgeable_members(guild)

        return [
            discord.Embed(
                title=f"{execution_mode} Purge - Purged {len(members)}",
                description=page,
                colour=discord.Colour.orange()
            )
            for page in pagify("\n".join(
                _get_safe_username(member)
                for member in members
                if await self._purge_member(member)
            ))
        ]

    async def _purge_member(self, member: discord.Member):
        try:
<<<<<<< Updated upstream
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
            if len(new_list) > 2048:
                break
            users_kicked = new_list

        data = discord.Embed(
            colour=discord.Colour.orange(),
            timestamp=datetime.utcnow()
        )
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

=======
            await member.kick()
            await self.config.increment_count(member.guild)
>>>>>>> Stashed changes
            return True
        except (discord.HTTPException, discord.Forbidden):
            return False

    async def get_purgeable_members(self, guild: discord.Guild) -> List[discord.Member]:
        """
        Gets members to purge.
        In addition, performs checks for excluded users.
        """
        to_purge: List[discord.Member] = []
        for member in guild.members:
            # If member has a role other than @everyone, they're safe
            if len(member.roles) > 1:
                continue

            # If member is older than the minimum age, they're safe
            time_limit = await self.config.get_age_threshold(guild)
            cutoff_date = datetime.utcnow() - timedelta(days=time_limit)
            if member.joined_at > cutoff_date:
                continue

            if not await self.config.member_is_excluded(guild, member):
                continue

            to_purge.append(member)

        return to_purge

    @commands.group(name="purge")
    @commands.guild_only()
    @checks.mod()
    async def _purge(self, ctx: commands.Context):
        pass

    @_purge.command("logchannel")
    async def purge_logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Logs details of purging to this channel.
        The bot must have permission to write to this channel.
        """
        await self.config.set_log_channel(ctx.guild, channel)
        await ctx.send("Purge log channel set.")

    @_purge.command("execute")
    async def purge_execute(self, ctx: commands.Context):
        """
        Executes a purge.
        Users will be **kicked** if they haven't verified.
        """
        purge_embeds = await self._purge_users(ctx.guild, "Manual")

        if not purge_embeds:
            await ctx.send("No users to purge.")
            return

        if not ctx.channel.permissions_for(ctx.me).embed_links:
            await ctx.channel.send("I need the `Embed links` permission to send a purge board.")
            return

        for embed in purge_embeds:
            await ctx.send(embed=embed)

    @_purge.command("simulate")
    async def purge_simulate(self, ctx: commands.Context):
        """
        Simulates a purge.
        Users will be **detected** if they haven't verified.
        """
        users = await self.get_purgeable_members(ctx.guild)

        embeds = [
            discord.Embed(
                title=f"Purge Simulation - Found {len(users)}",
                description=page,
                colour=await ctx.embed_colour()
            )
            for page in
            pagify("\n".join(
                _get_safe_username(m)
                for m in
                users
            ))
        ]

        if not ctx.channel.permissions_for(ctx.me).embed_links:
            await ctx.send("I need the `Embed links` permission to send a purge board.")
            return

        for embed in embeds:
            await ctx.send(embed=embed)

    @_purge.command("exclude")
    async def purge_exclude_user(self, ctx: commands.Context, member: discord.Member):
        """Excludes an otherwise eligible user from the purge."""
        await self.config.add_excluded_member(ctx.guild, member)
        await ctx.send("That user is now safe from pruning!")

    @_purge.command("include")
    async def purge_include_user(self, ctx: commands.Context, member: discord.Member):
        """Includes a possibly-eligible user in the purge checks."""
        await self.config.remove_excluded_member(ctx.guild, member)
        await ctx.send("That user is no longer safe from pruning!")

    @_purge.command("minage")
    async def purge_minage(self, ctx: commands.Context, min_age: int):
        """
        Sets the number of days a user can remain in the server with no
        roles before being purged.
        """
        if min_age < 1:
            await ctx.send("Minimum age can not be less than 1 day")
            return

        await self.config.set_age_threshold(ctx.guild, min_age)
        await ctx.send(f"Set the new minimum age to {min_age} days.")

    @_purge.command("schedule")
    async def purge_schedule(self, ctx: commands.Context, schedule: str):
        """Sets how often the bot should purge users.
        Accepts cron syntax. For instance `30 02 */2 * *` would be every 2
        days at 02:30.

        Example:
        - `[p]purge schedule "30 02 */2 * *"`
        """
        schedule_is_valid = await self.config.set_schedule(ctx.guild, schedule)

        if not schedule_is_valid:
            await ctx.send("The schedule given was invalid.")
        else:
            await ctx.send(f"Set the schedule to `{schedule_is_valid}`.")

    @_purge.command("enable")
    async def purge_enable(self, ctx: commands.Context):
        """Enables automated purges based on the schedule."""
        await self.config.enable(ctx.guild)
        await ctx.send("Enabled the purge task.")

    @_purge.command("disable")
    async def purge_disable(self, ctx: commands.Context):
        """Disables automated purges based on the schedule."""
        await self.config.disable(ctx.guild)
        await ctx.send("Disabled the purge task.")

    @_purge.command("status")
    async def purge_status(self, ctx: commands.Context):
        """
        Status of the bot.
        The bot will display how many users it has kicked
        since its inception.
        In addition, will also post its current configuration and status.
        """
        last_run = await self.config.get_last_run(ctx.guild)
        next_run = await self.config.get_next_run(ctx.guild)

        embed = (
            discord.Embed(colour=await ctx.embed_colour())
            .add_field(name="Enabled", value=str(await self.config.is_enabled(ctx.guild)))
            .add_field(name="Purged", value=f"{await self.config.get_count(ctx.guild)} users")
            .add_field(name="Min Age", value=f"{await self.config.get_age_threshold(ctx.guild)} days")
            .add_field(name="Log Channel", value=getattr(await self.config.get_log_channel(ctx.guild), "mention", "Not set"))
            .add_field(name="Last Run", value=last_run.strftime("%Y-%m-%d %H:%M:%SZ") if last_run is not None else "Never")
            .add_field(name="Next Run", value=next_run.strftime("%Y-%m-%d %H:%M:%SZ") if next_run is not None else "Not scheduled")
            .add_field(name="Schedule", value=await self.config.get_schedule(ctx.guild))
        )

        if not ctx.channel.permissions_for(ctx.me).embed_links:
            await ctx.send("I need the `Embed links` permission to send a purge status.")

        await ctx.send(embed=embed)
