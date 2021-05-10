from .jail import JailCog


def setup(bot):
    bot.add_cog(JailCog(bot))