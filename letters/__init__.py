from redbot.core.bot import Red

from .letters import Letters


async def setup(bot: Red):
    await bot.add_cog(Letters())
