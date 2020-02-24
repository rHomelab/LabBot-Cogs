from .ark import ARKCog


def setup(bot):
    bot.add_cog(ARKCog(bot))
