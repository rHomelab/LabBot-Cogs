from redbot.core.bot import Red

from .autoreply import AutoReplyCog


async def setup(bot: Red):
    await bot.add_cog(AutoReplyCog(bot))
