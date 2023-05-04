from redbot.core.bot import Red

from .custom_msg import CustomMsgCog


async def setup(bot: Red):
    await bot.add_cog(CustomMsgCog())
