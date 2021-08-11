"""discord red-bot notes"""
import typing
from datetime import datetime as dt

import discord
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page
from redbot.core.utils.mod import is_admin_or_superior

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class NotesCog(commands.Cog):
    """Notes Cog"""

    bot: Red
    config: Config

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=127318281)

        default_guild_settings = {"notes": [], "warnings": []}

        self.config.register_guild(**default_guild_settings)

    @commands.group(name="notes")
    @commands.guild_only()
    @checks.mod()
    async def _notes(self, ctx: commands.Context):
        pass

    @commands.group(name="warnings")
    @commands.guild_only()
    @checks.mod()
    async def _warnings(self, ctx: commands.Context):
        pass

    @_notes.command("add")
    async def notes_add(
        self,
        ctx: commands.Context,
        user: typing.Union[discord.Member, int],
        *,
        message: str,
    ):
        """Log a note against a user.

        Example:
        - `[p]notes add <user> <message>`
        """
        async with self.config.guild(ctx.guild).notes() as notes:
            notes.append(
                {
                    "id": len(notes) + 1,
                    "member": getattr(user, "id", user),
                    "message": message,
                    "deleted": False,
                    "reporter": ctx.author.id,
                    "reporterstr": ctx.author.name,
                    "date": dt.utcnow().timestamp(),
                }
            )
        await ctx.send("Note added.")

    @_warnings.command("add")
    async def warnings_add(
        self,
        ctx: commands.Context,
        user: typing.Union[discord.Member, int],
        *,
        message: str,
    ):
        """Log a warning against a user.

        Example:
        - `[p]warnings add <user> <message>`
        """
        async with self.config.guild(ctx.guild).warnings() as warnings:
            warnings.append(
                {
                    "id": len(warnings) + 1,
                    "member": getattr(user, "id", user),
                    "message": message,
                    "deleted": False,
                    "reporter": ctx.author.id,
                    "reporterstr": ctx.author.name,
                    "date": dt.utcnow().timestamp(),
                }
            )
        await ctx.send("Warning added.")

    @_notes.command("delete")
    async def notes_delete(self, ctx: commands.Context, note_id: int):
        """Deletes a note.

        Example:
        - `[p]notes delete <note id>`
        """
        async with self.config.guild(ctx.guild).notes() as notes:
            try:
                note = notes[note_id - 1]
            except IndexError:
                return await ctx.send("Note not found.")

            if not note["deleted"]:
                # User must be an admin or owner of the note
                if not (note["reporter"] == ctx.author.id or await is_admin_or_superior(ctx.bot, ctx.author)):
                    return await ctx.send("You don't have permission to do this.")

                # Delete note if not previously deleted
                note.update({"deleted": True})
                await ctx.send("Note deleted.")
            else:
                await ctx.send("Note already deleted.")

    @_warnings.command("delete")
    async def warning_delete(self, ctx: commands.Context, warning_id: int):
        """Deletes warning

        Example:
        - `[p]warnings delete <warning id>`
        """
        async with self.config.guild(ctx.guild).warnings() as warnings:
            try:
                warning = warnings[warning_id - 1]
            except IndexError:
                return await ctx.send("Warning not found.")

            if not warning["deleted"]:
                # User must be an admin or owner of the warning
                if not (warning["reporter"] == ctx.author.id or await is_admin_or_superior(self.bot, ctx.author)):
                    return await ctx.send("You don't have permission to do this.")

                # Delete warning if not previously deleted
                warning.update({"deleted": True})
                await ctx.send("Warning deleted.")
            else:
                await ctx.send("Warning already deleted.")

    @_notes.command("edit")
    async def notes_edit(self, ctx, note_id: int, *, content: str):
        """Edit the contents of a note

        Example:
        - `[p]notes edit 5 foo bar`"""
        async with self.config.guild(ctx.guild).notes() as notes:
            try:
                note = notes[note_id - 1]
            except IndexError:
                return await ctx.send("Note not found")

            if not (note["reporter"] == ctx.author.id or await is_admin_or_superior(self.bot, ctx.author)):
                return await ctx.send("You don't have permission to do this.")

            if note["deleted"]:
                return await ctx.send("You can't edit this note because it is deleted.")

            note.update({"message": content})
            await ctx.send("Note edited.")

    @_warnings.command("edit")
    async def warnings_edit(self, ctx, warning_id: int, *, content: str):
        """Edit the contents of a warning

        Example:
        - `[p]warnings edit 5 foo bar`"""
        async with self.config.guild(ctx.guild).warnings() as warnings:
            try:
                warning = warnings[warning_id - 1]
            except IndexError:
                return await ctx.send("Warning not found")

            if not (warning["reporter"] == ctx.author.id or await is_admin_or_superior(self.bot, ctx.author)):
                return await ctx.send("You don't have permission to do this.")

            if warning["deleted"]:
                return await ctx.send("You can't edit this warning because it is deleted.")

            warning.update({"message": content})
            await ctx.send("Warning edited.")

    @_notes.command("restore")
    async def notes_restore(self, ctx, note_id: int):
        """Restore a deleted note

        Example:
        - `[p]notes restore 5`
        """
        async with self.config.guild(ctx.guild).notes() as notes:
            try:
                note = notes[note_id - 1]
            except IndexError:
                return await ctx.send("Note not found")

            if not (note["reporter"] == ctx.author.id or await is_admin_or_superior(self.bot, ctx.author)):
                return await ctx.send("You don't have permission to do this.")

            if not note["deleted"]:
                return await ctx.send("You can't restore this note because it is not deleted.")

            note.update({"deleted": False})
            await ctx.send("Note restored.")

    @_warnings.command("restore")
    async def warnings_restore(self, ctx, warning_id: int):
        """Restore a deleted warning

        Example:
        - `[p]warnings restore 5`
        """
        async with self.config.guild(ctx.guild).warnings() as warnings:
            try:
                warning = warnings[warning_id - 1]
            except IndexError:
                return await ctx.send("Warning not found")

            if not (warning["reporter"] == ctx.author.id or await is_admin_or_superior(self.bot, ctx.author)):
                return await ctx.send("You don't have permission to do this.")

            if not warning["deleted"]:
                return await ctx.send("You can't restore this warning because it is not deleted.")

            warning.update({"deleted": False})
            await ctx.send("Warning restored.")

    @_notes.command("list", aliases=["view"])
    async def notes_list(self, ctx: commands.Context, user: typing.Union[discord.Member, int] = None):
        """Lists notes and warnings for everyone or a specific user.

        Example:
        - `[p]notes list <user>`
        - `[p]notes list`
        """
        user_id = getattr(user, "id", user)

        def note_to_dict(note: dict) -> dict:
            return {
                "id": note["id"],
                "member": ctx.guild.get_member(note["member"]) or note["member"],
                "modname": getattr(ctx.guild.get_member(note["reporter"]), "name", note["reporterstr"]),
                "display_time": int(note["date"]),
                "date": note["date"],
                "message": note["message"],
            }

        async with self.config.guild(ctx.guild).notes() as discord_notes:
            notes = [
                f"""📝#{note["id"]} **{note["member"]} - Added by {note["modname"]}** - <t:{note["display_time"]}:F>\n {note["message"]}"""
                for note in sorted(
                    [note_to_dict(n) for n in discord_notes if n["member"] == user_id and not n["deleted"]],
                    key=lambda n: n["date"],
                    reverse=True,
                )
            ]

        async with self.config.guild(ctx.guild).warnings() as discord_warnings:
            warnings = [
                f"""⚠️#{note["id"]} **{note["member"]} - Added by {note["modname"]}** - <t:{note["display_time"]}:F>\n {note["message"]}"""
                for note in sorted(
                    [note_to_dict(n) for n in discord_warnings if n["member"] == user_id and not n["deleted"]],
                    key=lambda n: n["date"],
                    reverse=True,
                )
            ]

        messages = "\n\n".join(warnings + notes)

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = pagify(messages, shorten_by=58)
        embeds = [
            discord.Embed(
                title=(
                    f"Notes for {user} - {len(warnings)} warnings, {len(notes)} notes"
                    if user
                    else f"All notes and warnings - {len(warnings)} warnings, {len(notes)} notes"
                ),
                description=page,
                colour=await ctx.embed_colour(),
            )
            for page in pages
        ]

        # Menu implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/d6f9ddc3afe00ac1e8b4925a73f6783a3f497b9e/redbot/core/utils/menus.py#L18
        if embeds:
            await menu(
                ctx,
                pages=embeds,
                controls=CUSTOM_CONTROLS,
                message=None,
                page=0,
                timeout=30,
            )
        else:
            await ctx.send("No notes to display.")

    @_notes.command("status")
    async def notes_status(self, ctx: commands.Context):
        """Status of the cog.
        The bot will display how many notes it has recorded
        since it's inception.

        Example:
        - `[p]notes status`
        """
        async with self.config.guild(ctx.guild).notes() as notes:
            discord_notes = notes
        async with self.config.guild(ctx.guild).warnings() as warnings:
            discord_warnings = warnings
        data = (
            discord.Embed(title="Notes Status", colour=await ctx.embed_colour())
            .add_field(name="Notes", value=f"{len(discord_notes)} notes")
            .add_field(name="Warnings", value=f"{len(discord_warnings)} warnings")
        )
        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to send a notes status.")
