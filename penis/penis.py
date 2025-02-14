import random

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify


class Penis(commands.Cog):
    """Penis related commands."""

    def __init__(self):
        pass

    @commands.command()
    async def penis(self, ctx, *users: discord.Member):
        """Detects user's penis length

        This is 100% accurate.
        Enter multiple users for an accurate comparison!"""

        dongs = {}
        msg = ""
        state = random.getstate()

        if len(users) == 0:
            users = (ctx.author,)

        for user in users:
            random.seed(user.id)
            dongs[user] = "8{}D".format("=" * random.randint(0, 30))

        random.setstate(state)
        dongs = sorted(dongs.items(), key=lambda x: x[1])

        for user, dong in dongs:
            if len(dong) <= 6:  # noqa: PLR2004
                msg += "**{}'s size:**\n{}\nlol small\n".format(user.display_name, dong)
            else:
                msg += "**{}'s size:**\n{}\n".format(user.display_name, dong)

        for page in pagify(msg):
            await ctx.send(page)
