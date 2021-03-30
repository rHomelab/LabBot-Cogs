from .uptimestats import UptimeStatsCog


def setup(bot):
    bot.add_cog(UptimeStatsCog(bot))
