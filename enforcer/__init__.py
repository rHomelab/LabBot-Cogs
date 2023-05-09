from redbot.core.bot import Red

from .enforcer import EnforcerCog


async def setup(bot: Red):
    await bot.add_cog(EnforcerCog(bot))
