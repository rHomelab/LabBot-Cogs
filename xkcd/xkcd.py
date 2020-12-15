from redbot.core import commands
import discord
import random
import asyncio,aiohttp,async_timeout,json


#Define function to do web requests
async def fetchGet(urlIn):
    async with aiohttp.ClientSession() as session:
        with async_timeout.timeout(10):
            async with session.get(urlIn) as response:
                await session.close()
                return await response.text()

class Xkcd(commands.Cog):
    """xkcd Cog"""

    def __init__(self):
        pass

    @commands.command()
    async def xkcd(self, ctx, comicNumber: int = 0):
        """Returns xkcd comic of given number, otherwise return latest comic."""
        
        #Because Randall is very funny comic #404 doen't exist
        if comicNumber == 404:
            xkcdEmbed = discord.Embed(title='404', colour=ctx.guild.me.colour)
            await ctx.send(embed=xkcdEmbed)
            return
        if comicNumber == 0:
            #No comic specified get latest
            url = "https://xkcd.com/info.0.json"
        else:
            url = f"https://xkcd.com/{comicNumber}/info.0.json"
        
        #Get comic data from xkcd api
        comicJson = await fetchGet(url)
        #Load as json
        comicJson = json.loads(comicJson)

        #Build embed for xkcd comic
        
        xkcdEmbed = discord.Embed(title='xkcd Comic: #{}'.format(comicJson["num"]), colour=ctx.guild.me.colour)
        xkcdEmbed.add_field(name="Comic Title", value=comicJson["safe_title"])
        xkcdEmbed.add_field(name="Publish Date", value=comicJson["year"]+"-"+comicJson["month"]+"-"+comicJson["day"])
        #If there is alt text add it to the embed, otherwise don't
        if comicJson["alt"] != "":
            xkcdEmbed.add_field(name="Comic Alt Text", value=comicJson["alt"])
        else:
            pass
        xkcdEmbed.set_image(url=comicJson["img"])
        

        await ctx.send(embed=xkcdEmbed)