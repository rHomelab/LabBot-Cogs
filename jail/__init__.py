from redbot.core.bot import Red

from .jail import JailCog


async def setup(bot: Red):
    await bot.add_cog(JailCog(bot))
