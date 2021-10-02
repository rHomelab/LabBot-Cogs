from .custommessage import CustomMsgCog
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(CustomMsgCog())
