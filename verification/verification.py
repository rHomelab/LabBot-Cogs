"""discord red-bot verification"""
from redbot.core import commands


class VerificationCog(commands.Cog):
    """Verification Cog"""

    def __init__(self, bot):
        self.bot = bot
