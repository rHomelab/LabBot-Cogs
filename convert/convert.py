from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
import discord
from pint import UnitRegistry

class Convert(commands.Cog):
    """Convert related commands."""

    def __init__(self):
        self.__ureg = UnitRegistry()

    @commands.command()
    async def convert(self, ctx, *unit):
        """Convert to different kinds of units to other units

        Uses pint to support most units available"""

        try:
            src, dst = ' '.join(unit).split(' to ')

            question = self.__ureg(src)
        except:
            return

        try:
            answer = question.to(dst)
        except DimensionalityError:
            msg = "*Unable to convert {}*".format(question.to_compact())
        else:
            msg = "{} is {}".format(question.to_compact(), answer.to_compact())

        for page in pagify(msg):
            await ctx.send(page)