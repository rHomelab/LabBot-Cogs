from redbot.core.bot import Red

from .custom_msg import CustomMsgCog


def setup(bot: Red):
    bot.add_cog(CustomMsgCog())
