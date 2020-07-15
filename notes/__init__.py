from .notes import NotesCog


def setup(bot):
    bot.add_cog(NotesCog(bot))
