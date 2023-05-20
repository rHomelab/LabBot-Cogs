from redbot.core.bot import Red

from .profilewatch import ProfileWatchCog


async def setup(bot: Red):
    await bot.add_cog(ProfileWatchCog(bot))
