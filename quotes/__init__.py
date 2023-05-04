from redbot.core.bot import Red

from .quotes import QuotesCog


async def setup(bot: Red):
    await bot.add_cog(QuotesCog(bot))
