from redbot.core.bot import Red

from .purge import PurgeCog


async def setup(bot: Red):
    await bot.add_cog(PurgeCog(bot))
