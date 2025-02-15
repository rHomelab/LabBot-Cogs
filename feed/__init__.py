from discord import AppCommandType
from redbot.core.bot import Red

from .feed import FeedCog, on_message, on_user


async def setup(bot: Red):
    await bot.add_cog(FeedCog())
    bot.tree.add_command(on_message)
    bot.tree.add_command(on_user)


async def teardown(bot: Red):
    bot.tree.remove_command("Feed", type=AppCommandType.message)
    bot.tree.remove_command("Feed", type=AppCommandType.user)
