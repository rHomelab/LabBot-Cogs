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
        """Performs a execution on who to purge.
        Users will be **kicked** if they haven't verified.

        Example:
        - `[p]purge execute`
        """
        pass

    @_purge.command("simulate")
    async def purge_simulate(self, ctx: commands.Context):
        """Performs a simulation on who to purge.
        Users will be **detected** if they haven't verified.

        Example:
        - `[p]purge simulate`
        """
        pass

    @_purge.command("exclude")
    async def purge_exclude_user(self, ctx: commands.Context):
        """Excludes a user from being detected by the purge.

        Example:
        - `[p]purge exclude <user>`
        """
        pass

    @_purge.command("setlimit")
    async def purge_setlimit(self, ctx: commands.Context):
        """Sets the limit of days to retain users.

        Example:
        - `[p]purge setlimit <days>`
        """
        pass

    @_purge.command("runevery")
    async def purge_runevery(self, ctx: commands.Context):
        """Sets how often the bot should purge users.

        Example:
        - `[p]purge runevery <minutes>`
        """
        pass

    @_purge.command("enable")
    async def purge_enable(self, ctx: commands.Context):
        """Enables the bot.
        The bot will be enabled if this command is run.

        Example:
        - `[p]purge enable`
        """
        pass

    @_purge.command("disable")
    async def purge_disable(self, ctx: commands.Context):
        """Disables the bot.
        The bot will be disabled if this command is run.

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
