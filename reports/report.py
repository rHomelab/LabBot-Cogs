"""discord red-bot report cog"""
from redbot.core import commands, Config


class ReportCog(commands.Cog):
    """Report Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=1092901)
