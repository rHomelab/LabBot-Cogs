from redbot.core.bot import Red

from .feed import FeedCog


async def setup(bot: Red):
    await bot.add_cog(FeedCog())
