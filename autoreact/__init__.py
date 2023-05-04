from redbot.core.bot import Red

from .autoreact import AutoReactCog


async def setup(bot: Red):
    await bot.add_cog(AutoReactCog(bot))
