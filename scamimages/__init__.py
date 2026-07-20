from redbot.core.bot import Red

from .scamimages import ScamImagesCog


async def setup(bot: Red):
    await bot.add_cog(ScamImagesCog(bot))
