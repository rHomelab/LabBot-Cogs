"""discord red-bot notes"""
import discord
from redbot.core import commands, Config, checks


class NotesCog(commands.Cog):
    """Notes Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = Config.get_conf(self, identifier=127318281)

        default_guild_settings = {
            "notes": [],
            "warnings": []
        }

        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="notes")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _notes(self, ctx: commands.Context):
        pass

    @_notes.command("status")
    async def notes_status(self, ctx: commands.Context):
        """Status of the cog.
        The bot will display how many notes it has recorded
        since it's inception.

        Example:
        - `[p]notes status`
        """
        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.title = "Notes Status"

        async with self.settings.guild(ctx.guild).notes() as li:
            data.add_field(name="Count", value=f"{len(li)} notes")

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " +
                           "send a notes status.")
