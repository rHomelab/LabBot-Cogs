from redbot.core.bot import Red

from .voicewatch import VoiceWatchCog


async def setup(bot: Red):
    await bot.add_cog(VoiceWatchCog(bot))
