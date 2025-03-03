import random

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.mod import is_mod_or_superior

DONG_DISTRIBUTION_CONST = 30
SMALL_DONG_CONST = 6
BIG_DONG_CONST = DONG_DISTRIBUTION_CONST - SMALL_DONG_CONST
VIP_DONG_CONST = DONG_DISTRIBUTION_CONST + 5


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
            dongs[user] = ("8{}D".format("=" * random.randint(0, DONG_DISTRIBUTION_CONST)),
                           VIP_DONG_CONST)[await is_mod_or_superior(ctx.bot, user)]

        random.setstate(state)
        dongs = sorted(dongs.items(), key=lambda x: x[1])

        for user, dong in dongs:
            if len(dong) <= SMALL_DONG_CONST:
                msg += "**{}'s size:**\n{}\nlol small\n".format(user.display_name, dong)
            elif len(dong) <= BIG_DONG_CONST:
                msg += "**{}'s size:**\n{}\n".format(user.display_name, dong)
            else:
                if len(dong) == VIP_DONG_CONST:
                    msg += "**{}'s size:**\n{}\nYou thought you could dick measure your way out of this one?\n"\
                        .format(user.display_name, dong)
                else:
                    msg += "**{}'s size:**\n{}\nwow, now that's a dong!\n".format(user.display_name, dong)

        for page in pagify(msg):
            await ctx.send(page)
