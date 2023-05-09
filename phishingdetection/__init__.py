from redbot.core.bot import Red

from .phishingdetection import PhishingDetectionCog


async def setup(bot: Red):
    await bot.add_cog(PhishingDetectionCog(bot))
