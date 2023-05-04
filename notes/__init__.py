from redbot.core.bot import Red

from .notes import NotesCog


async def setup(bot: Red):
    await bot.add_cog(NotesCog())
