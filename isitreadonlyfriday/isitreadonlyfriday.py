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
                "GET", f"https://isitreadonlyfriday.com/api/isitreadonlyfrida/{offset}"
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
        """Returns isitreadonlyfriday result with given offset (default 0)"""

        embed = await self.get_isitreadonlyfriday(offset)
        await ctx.send(embed=embed)

    @app_commands.command(name="isitreadonlyfriday")
    async def app_isitreadonlyfriday(
        self, interaction: discord.Interaction, offset: int = 0
    ):
        """Returns isitreadonlyfriday result"""

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
