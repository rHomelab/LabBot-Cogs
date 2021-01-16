import urllib.parse
from redbot.core import commands

class Google(commands.Cog):
    """Google Command"""

    def __init__(self):
        pass

    @commands.command()
    async def google(self, ctx, *, query):
        """Send a google link with provided query"""
        await ctx.send("https://google.com/search?q="+urllib.parse.quote_plus(query))
