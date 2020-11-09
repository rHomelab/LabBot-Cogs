from .verify import VerifyCog


def setup(bot):
    bot.add_cog(VerifyCog(bot))
