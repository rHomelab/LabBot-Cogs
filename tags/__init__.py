from redbot.core.bot import Red

from .tags import TagCog


async def setup(bot: Red):
    await bot.add_cog(TagCog(bot))
