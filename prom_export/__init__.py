import time

from redbot.core.bot import Red

from .main import PromExporter


async def setup(bot: Red):
    prom = PromExporter(bot)
    await prom.init()
    await bot.add_cog(prom)

