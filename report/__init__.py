from redbot.core.bot import Red

from .report import ReportCog


def setup(bot: Red):
    bot.add_cog(ReportCog(bot))
