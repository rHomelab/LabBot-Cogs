from redbot.core.bot import Red

from .bancount import BanCountCog


async def setup(bot: Red):
    await bot.add_cog(BanCountCog(bot))
