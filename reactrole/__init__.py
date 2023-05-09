from redbot.core.bot import Red

from .reactrole import ReactRoleCog


async def setup(bot: Red):
    await bot.add_cog(ReactRoleCog(bot))
