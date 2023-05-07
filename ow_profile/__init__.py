from redbot.core.bot import Red

from .owprofile import OWProfileCog


async def setup(bot: Red):
    await bot.add_cog(OWProfileCog(bot))
