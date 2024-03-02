import discord
from redbot.core import commands, Config, checks
from redbot.core.bot import Red


class JailCog(commands.Cog):
    """Jail cog"""

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

        self.config = Config.get_conf(self, identifier=1289862744207523842002)

    @checks.mod()
    @commands.guild_only()
    @commands.group("jail", pass_context=True, invoke_without_command=True)
    async def _jail(self, ctx: commands.Context, user: discord.User):
        """Jails the specified user."""
        pass

    @checks.admin()
    @_jail.command("setup")
    async def _jail_setup(self, ctx: commands.Context, cat_id: str, channel: discord.TextChannel):
        """Sets the jail category and template channel."""
        pass
