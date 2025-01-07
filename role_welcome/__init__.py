from redbot.core.bot import Red

from .role_welcome import RoleWelcomeCog


async def setup(bot: Red):
    await bot.add_cog(RoleWelcomeCog(bot))
