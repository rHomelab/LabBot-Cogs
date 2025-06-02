from redbot.core.bot import Red

from .guild_profiles import GuildProfilesCog


async def setup(bot: Red):
    await bot.add_cog(GuildProfilesCog(bot))
