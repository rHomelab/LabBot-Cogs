import urllib.parse

import discord
from redbot.core import commands


class LatexCog(commands.Cog):
    """Latex Cog"""

    @commands.command()
    async def latex(self, ctx: commands.Context, *, latex: str):
        """Render a LaTeX statement

        Example:
        - `[p]latex <LaTeX statement>`
        """
        embed = await self.make_latex_embed(ctx, latex)
        await ctx.send(embed=embed)
        await ctx.message.delete()

    async def make_latex_embed(self, ctx: commands.Context, latex) -> discord.Embed:
        url = "https://latex.codecogs.com/png.image?" + urllib.parse.quote_plus(latex)
        latex_embed = discord.Embed(title="LaTeX Rendering", colour=await ctx.embed_colour())
        latex_embed.add_field(name="Requested by:", value=ctx.author.mention)
        latex_embed.set_image(url=url)
        return latex_embed
