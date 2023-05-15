from redbot.core.bot import Red

from .owvoice import OWVoiceCog


async def setup(bot: Red):
    await bot.add_cog(OWVoiceCog(bot))
