import aiohttp
import discord
from redbot.core import commands


async def fetch_get(url_in: str) -> dict:
    """Make web requests"""
    async with aiohttp.request("GET", url_in) as response:
        if response.status != 200:
            return {}
        return await response.json()


class Xkcd(commands.Cog):
    """xkcd Cog"""

    def __init__(self):
        pass

    @commands.command()
    async def xkcd(self, ctx: commands.Context, comic_number: int = 0):
        """Returns xkcd comic of given number, otherwise return latest comic."""

        if not comic_number:
            # No comic specified, get latest
            url = "https://xkcd.com/info.0.json"
        else:
            url = f"https://xkcd.com/{comic_number}/info.0.json"

        # Get comic data from xkcd api
        comic_json = await fetch_get(url)

        # If the response isn't 200 throw an error
        if not comic_json:
            embed = await self.make_error_embed(ctx, "404")
            await ctx.send(embed=embed)
            return

        embed = await self.make_comic_embed(ctx, comic_json)
        await ctx.send(embed=embed)

    async def make_comic_embed(self, ctx: commands.Context, data: dict) -> discord.Embed:
        """Generate embed for xkcd comic"""
        xkcd_embed = discord.Embed(
            title=f"xkcd Comic: #{data['num']}", url=f"https://xkcd.com/{data['num']}", colour=await ctx.embed_colour()
        )
        xkcd_embed.add_field(name="Comic Title", value=data["safe_title"])
        xkcd_embed.add_field(name="Publish Date", value=f"{data['year']}-{data['month']}-{data['day']}")
        # If there is alt text add it to the embed, otherwise don't
        if data["alt"]:
            xkcd_embed.add_field(name="Comic Alt Text", value=data["alt"])
        else:
            pass
        xkcd_embed.set_image(url=data["img"])
        return xkcd_embed

    async def make_error_embed(self, ctx: commands.Context, error_type: str) -> discord.Embed:
        "Generate error message embeds"
        error_msgs = {"404": "Comic not found"}
        return discord.Embed(
            title="Error",
            description=error_msgs[error_type],
            colour=await ctx.embed_colour(),
        )
