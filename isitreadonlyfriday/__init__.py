from redbot.core.bot import Red

from .isitreadonlyfriday import IsItReadOnlyFriday


async def setup(bot: Red):
    await bot.add_cog(IsItReadOnlyFriday())
