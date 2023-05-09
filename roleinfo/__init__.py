from redbot.core.bot import Red

from .roleinfo import RoleInfoCog


async def setup(bot: Red):
    await bot.add_cog(RoleInfoCog(bot))
