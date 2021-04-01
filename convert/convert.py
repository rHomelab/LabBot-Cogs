import discord
from pint import UnitRegistry
from redbot.core import commands


class Convert(commands.Cog):
    """Convert related commands."""

    def __init__(self):
        self.__ureg = UnitRegistry()

    @commands.command()
    async def convert(self, ctx, *unit):
        """Convert from different kinds of units to other units using pint

        Example:
        - `[p]convert <from> to <to>`
        - `[p]convert 23cm to in`
        - `[p]convert 5in + 5ft to cm`
        """

        try:
            src, dst = " ".join(unit).split(" to ")
            question = self.__ureg(src)
            answer = question.to(dst)
        except Exception:
            error_embed = discord.Embed(
                title="Error",
                description=f"Unable to convert `{' '.join(unit)}`",
                colour=await ctx.embed_colour(),
            )
            await ctx.send(embed=error_embed)
        else:
            msg = f"{question.to_compact()} is {answer.to_compact()}"
            await ctx.send(msg)
