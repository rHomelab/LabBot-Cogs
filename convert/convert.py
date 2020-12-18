from redbot.core import commands
import discord
from pint import UnitRegistry

class Convert(commands.Cog):
    """Convert related commands."""

    def __init__(self):
        self.__ureg = UnitRegistry()

    @commands.command()
    async def convert(self, ctx, *unit):
        """Convert to different kinds of units to other units

        example - `[p]convert 5kg to lb`"""

        try:
            src, dst = ' '.join(unit).split(' to ')
            question = self.__ureg(src)
            answer = question.to(dst)
        except:
            colour = await ctx.embed_colour()
            error_embed = discord.Embed(title='Error', description=f"*Unable to convert {question.to_compact()}*", colour=colour)
            await ctx.send(embed=error_embed)
        else:
            msg = f"{question.to_compact()} is {answer.to_compact()}"
            await ctx.send(msg)
