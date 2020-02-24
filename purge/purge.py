"""discord red-bot purge"""
from redbot.core import commands


class PurgeCog(commands.Cog):
    """Purge Cog"""

    def __init__(self, bot):
        self.bot = bot
