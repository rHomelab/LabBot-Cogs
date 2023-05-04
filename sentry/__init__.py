from redbot.core.bot import Red

from .sentry import SentryCog


async def setup(bot: Red):
    await bot.add_cog(SentryCog(bot))
