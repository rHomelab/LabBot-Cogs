from redbot.core.bot import Red

from .verify import VerifyCog


async def setup(bot: Red):
    await bot.add_cog(VerifyCog(bot))
