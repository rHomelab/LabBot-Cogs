from redbot.core.bot import Red

from .xkcd import Xkcd


async def setup(bot: Red):
    await bot.add_cog(Xkcd())
