from .enforcer import EnforcerCog


def setup(bot):
    bot.add_cog(EnforcerCog(bot))
