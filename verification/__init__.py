from .verification import VerificationCog


def setup(bot):
    bot.add_cog(VerificationCog(bot))
