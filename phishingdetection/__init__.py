from .phishingdetection import PhishingDetectionCog
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(PhishingDetectionCog(bot))
