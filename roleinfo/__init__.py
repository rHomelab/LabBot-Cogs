from redbot.core.bot import Red

from .roleinfo import RoleInfoCog


def setup(bot: Red):
    bot.add_cog(RoleInfoCog(bot))
