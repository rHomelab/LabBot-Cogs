from .purge import PurgeCog


def setup(bot):
    bot.add_cog(PurgeCog(bot))
