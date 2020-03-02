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

    @commands.group(name="warnings")
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def _warnings(self, ctx: commands.Context):
        pass

    @_notes.command("add")
    async def notes_add(
        self,
        ctx: commands.Context,
        user: discord.Member,
        *,
        message: str
    ):
        """Add a note to a user

        Example:
        - `[p]notes add <user> <message>`
        """
        async with self.settings.guild(ctx.guild).notes() as li:
            li.append(
                {
                    "member": user.id,
                    "message": message,
                    "deleted": False
                }
            )
        await ctx.send("Note added.")

    @_warnings.command("add")
    async def warnings_add(
        self,
        ctx: commands.Context,
        user: discord.Member,
        *,
        message: str
    ):
        """Add a warning to a user

        Example:
        - `[p]warnings add <user> <message>`
        """
        async with self.settings.guild(ctx.guild).warnings() as li:
            li.append(
                {
                    "member": user.id,
                    "message": message,
                    "deleted": False
                }
            )
        await ctx.send("Warning added.")

    @_notes.command("delete")
    async def notes_delete(
        self,
        ctx: commands.Context,
        note_id: int
    ):
        """Deletes note

        Example:
        - `[p]notes delete <note id>`
        """
        async with self.settings.guild(ctx.guild).notes() as li:
            if not li[note_id]["deleted"]:
                # Delete note if not previously deleted
                li[note_id]["deleted"] = True
                await ctx.send("Note deleted.")
                return

            await ctx.send("Note not found.")

    @_warnings.command("delete")
    async def warning_delete(
        self,
        ctx: commands.Context,
        warning_id: int
    ):
        """Deletes warning

        Example:
        - `[p]warnings delete <warning id>`
        """
        async with self.settings.guild(ctx.guild).warnings() as li:
            if not li[warning_id]["deleted"]:
                # Delete warning if not previously deleted
                li[warning_id]["deleted"] = True
                await ctx.send("Warning deleted.")
                return

            await ctx.send("Warning not found.")

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
