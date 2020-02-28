"""discord red-bot notes"""
from redbot.core import commands, Config


class NotesCog(commands.Cog):
    """Notes Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=127318281)
