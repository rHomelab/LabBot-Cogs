from .reactrole import ReactRoleCog


def setup(bot):
    bot.add_cog(ReactRoleCog(bot))
