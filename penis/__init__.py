from redbot.core.bot import Red

from .penis import Penis


async def setup(bot: Red):
    await bot.add_cog(Penis())
