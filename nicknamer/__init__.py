from .nicknamer import NicknamerCog


def setup(bot):
    bot.add_cog(NicknamerCog(bot))
