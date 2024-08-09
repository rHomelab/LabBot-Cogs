import asyncio
import logging

import aiohttp
import discord
from redbot.core import app_commands, commands

log = logging.getLogger("red.rhomelab.isitreadonlyfriday")


class IsItReadOnlyFriday(commands.Cog):
    """IsItReadOnlyFriday Cog"""

    def __init__(self):
        pass

    async def get_isitreadonlyfriday(self, offset: int) -> discord.Embed:
        # Get readonly data from isitreadonlyfriday api
        try:
            async with aiohttp.request(
                "GET", f"https://isitreadonlyfriday.com/api/isitreadonlyfriday/{offset}"
            ) as response:
                response.raise_for_status()
                try:
                    readonly = await response.json()
                except aiohttp.ContentTypeError:
                    readonly = {"error": "Response content is not JSON"}
        except aiohttp.ClientError as e:
            readonly = {"error": f"Client error: {str(e)}"}
        except asyncio.TimeoutError:
            readonly = {"error": "Request timed out"}
        except Exception as e:
            readonly = {"error": f"An unexpected error occurred: {str(e)}"}

        if readonly.get("error"):
            log.error(f"Error fetching data from API: {readonly['error']}")
            return await self.make_error_embed()

        return await self.make_readonly_embed(readonly)

    @commands.command()
    async def isitreadonlyfriday(self, ctx: commands.Context, offset: int = 0) -> None:
        """Tells you if it's read-only Friday!

        Accepts optional UTC offset (default 0, range -12 to 12).
        """

        if offset not in range(-12, 13):
            await ctx.send("Offset must be between -12 and 12.")
            return

        embed = await self.get_isitreadonlyfriday(offset)
        await ctx.send(embed=embed)

    @app_commands.command(name="isitreadonlyfriday")
    async def app_isitreadonlyfriday(
        self,
        interaction: discord.Interaction,
        offset: app_commands.Range[int, -12, 12] = 0,
    ):
        """Tells you if it's read-only Friday!

        Paramters
        ----------
        offset: int
            UTC offset (default 0, range -12 to 12)
        """

        embed = await self.get_isitreadonlyfriday(offset)
        await interaction.response.send_message(embed=embed)

    @staticmethod
    async def make_readonly_embed(data: dict) -> discord.Embed:
        """Generate embed for isitreadonlyfriday readonly"""
        if data["readonly"]:
            return discord.Embed(
                title="Is It Read-Only Friday?",
                description="Yes! Don't change anything!",
                colour=discord.Colour.red(),
            )

        return discord.Embed(
            title="Is It Read-Only Friday?",
            description="No! Change away!",
            colour=discord.Colour.green(),
        )

    @staticmethod
    async def make_error_embed() -> discord.Embed:
        """Generate error message embeds"""
        return discord.Embed(
            title="Error",
            description="An error occurred while fetching data from isitreadonlyfriday.com",
            colour=discord.Colour.brand_red(),
        )
