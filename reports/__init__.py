from .report import ReportCog


def setup(bot):
    bot.add_cog(Report(bot))
