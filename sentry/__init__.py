from .sentry import SentryCog


def setup(bot):
    bot.add_cog(SentryCog(bot))
