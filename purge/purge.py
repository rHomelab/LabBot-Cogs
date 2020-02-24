"""discord red-bot purge"""
from redbot.core import commands


class PurgeCog(commands.Cog):
    """Purge Cog"""

    def __init__(self, bot):
        self.bot = bot

    def get_purgeable_users(self):
        """
        Gets users to purge.
        In addition, performs checks for excluded users.
        """
        return []

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
        pass

    @_purge.command("exclude")
    async def purge_exclude_user(self, ctx: commands.Context):
        """Excludes an otherwise eligible user from the purge.

        Example:
        - `[p]purge exclude <user>`
        """
        pass

    @_purge.command("setlimit")
    async def purge_setlimit(self, ctx: commands.Context):
        """Sets the number of days a user can remain in the server with no roles before being purged.

        Example:
        - `[p]purge setlimit <days>`
        """
        pass

    @_purge.command("schedule")
    async def purge_schedule(self, ctx: commands.Context):
        """Sets how often the bot should purge users.
        Accepts cron syntax. For instance `30 02 */2 * *` would be every 2 days at 02:30.

        Example:
        - `[p]purge schedule <cron schedule>`
        - `[p]purge schedule 30 02 */2 * *`
        """
        pass

    @_purge.command("enable")
    async def purge_enable(self, ctx: commands.Context):
        """Enables automated purges based on the schedule.

        Example:
        - `[p]purge enable`
        """
        pass

    @_purge.command("disable")
    async def purge_disable(self, ctx: commands.Context):
        """Disables automated purges based on the schedule.

        Example:
        - `[p]purge disable`
        """
        pass

    @_purge.command("status")
    async def purge_status(self, ctx: commands.Context):
        """Status of the bot.
        The bot will display how many users it has kicked
        since it's inception.
        In addition, will also post its current configuration and status.

        Example:
        - `[p]purge status`
        """
        pass
