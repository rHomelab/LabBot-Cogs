from redbot.core.bot import Red

from .role_welcome import RoleWelcome


async def setup(bot: Red):
    await bot.add_cog(RoleWelcome(bot))
