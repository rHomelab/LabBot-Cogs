from redbot.core.bot import Red

from .google import Google


async def setup(bot: Red):
    await bot.add_cog(Google())
