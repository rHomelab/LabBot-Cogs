from redbot.core.bot import Red

from .topic import Topic

async def setup(bot: Red):
    await bot.add_cog(Topic())