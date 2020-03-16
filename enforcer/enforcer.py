"""discord red-bot enforcer"""
from redbot.core import commands, Config, checks


class EnforcerCog(commands.Cog):
    """Enforcer Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=987342593)

        default_guild_settings = {
            "channels": []
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="enforcer")
    @commands.guild_only()
    @checks.admin()
    async def _enforcer(self, ctx: commands.Context):
        pass
