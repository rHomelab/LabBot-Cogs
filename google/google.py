import urllib.parse

from redbot.core import commands


class Google(commands.Cog):
    """Google Command"""

    @commands.command()
    async def google(self, ctx, *, query):
        """Send a google link with provided query"""
        if query.lower() == "google":
            await ctx.send("Great, nice one, thanks mate, now the internet's broken. Are you proud of yourself?")
        else:
            await ctx.send("https://google.com/search?q=" + urllib.parse.quote_plus(query))
