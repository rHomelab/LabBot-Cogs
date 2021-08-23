from redbot.core.bot import Red

from .tags import TagsCog


def setup(bot: Red):
    bot.add_cog(TagsCog())
