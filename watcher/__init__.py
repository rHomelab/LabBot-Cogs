from redbot.core.bot import Red

from .watcher import WatcherCog


async def setup(bot: Red):
    await bot.add_cog(WatcherCog(bot))
