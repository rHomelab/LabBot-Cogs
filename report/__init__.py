from redbot.core.bot import Red

from .report import ReportCog


async def setup(bot: Red):
    await bot.add_cog(ReportCog(bot))
