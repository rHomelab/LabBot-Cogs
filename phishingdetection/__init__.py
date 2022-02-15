from redbot.core.bot import Red

from .phishingdetection import PhishingDetectionCog


def setup(bot: Red):
    bot.add_cog(PhishingDetectionCog(bot))
