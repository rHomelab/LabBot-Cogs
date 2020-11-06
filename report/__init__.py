from .report import ReportCog


def setup(bot):
    bot.add_cog(ReportCog(bot))
