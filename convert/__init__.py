from redbot.core.bot import Red

from .convert import Convert


async def setup(bot: Red):
    await bot.add_cog(Convert())
