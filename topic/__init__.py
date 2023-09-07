from redbot.core.bot import Red

from .topic import Topic


async def setup(bot: Red):
    """Base setup function"""
    await bot.add_cog(Topic())
