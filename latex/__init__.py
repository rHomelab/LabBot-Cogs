from redbot.core.bot import Red

from .latex import LatexCog


async def setup(bot: Red):
    await bot.add_cog(LatexCog())
