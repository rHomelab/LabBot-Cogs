from redbot.core.bot import Red

from .notes import NotesCog


def setup(bot: Red):
    bot.add_cog(NotesCog())
