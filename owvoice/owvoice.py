from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import commands


class OWVoiceCog(commands.Cog):
    """Overwatch Voice Cog"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=128986274420752384003)

        default_guild_config = {
            "logchannel": "",  # Channel to send alerts to
            "": ""
        }

        self.config.register_guild(**default_guild_config)