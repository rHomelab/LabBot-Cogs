from redbot.core.bot import Red

from .betterping import BetterPing


async def setup(bot: Red) -> None:
    # Find built-in ping command and replace it
    old_ping = bot.get_command("ping")
    if old_ping:
        bot.remove_command(old_ping.name)
    await bot.add_cog(BetterPing(bot, old_ping))
