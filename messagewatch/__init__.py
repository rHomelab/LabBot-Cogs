from redbot.core.bot import Red

from .messagewatch import MessageWatchCog


async def setup(bot: Red):
    await bot.add_cog(MessageWatchCog(bot))
