"""discord red-bot notes"""
import typing
from datetime import datetime

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page
from redbot.core.utils.mod import is_admin_or_superior

CUSTOM_CONTROLS = {"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}


class NotesCog(commands.Cog):
    """Notes Cog"""

    def __init__(self, bot):
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
        user: typing.Union[discord.Member, str],
        *,
        message: str,
    ):
        """Log a note against a user.

        Example:
        - `[p]notes add <user> <message>`
        """
        current_date = datetime.utcnow()
        user_id = user if isinstance(user, str) else user.id

        # Save note to list
        async with self.config.guild(ctx.guild).notes() as notes:
            notes.append(
                {
                    "id": len(notes) + 1,
                    "member": user_id,
                    "message": message,
                    "deleted": False,
                    "reporter": ctx.author.id,
                    "reporterstr": ctx.author.name,
                    "date": current_date.timestamp(),
                }
            )
        await ctx.send("Note added.")

    @_warnings.command("add")
    async def warnings_add(
        self,
        ctx: commands.Context,
        user: typing.Union[discord.Member, str],
        *,
        message: str,
    ):
        """Log a warning against a user.

        Example:
        - `[p]warnings add <user> <message>`
        """
        current_date = datetime.utcnow()
        user_id = user if isinstance(user, str) else user.id

        async with self.config.guild(ctx.guild).warnings() as guilds:
            guilds.append(
                {
                    "id": len(guilds) + 1,
                    "member": user_id,
                    "message": message,
                    "deleted": False,
                    "reporter": ctx.author.id,
                    "reporterstr": ctx.author.name,
                    "date": current_date.timestamp(),
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
                if not note["deleted"]:
                    # User must be an admin or owner of the note
                    if not (note["reporter"] == ctx.author.id or await is_admin_or_superior(ctx.bot, ctx.author)):
                        await ctx.send("You don't have permission to do this.")
                        return

                    # Delete note if not previously deleted
                    note["deleted"] = True
                    await ctx.send("Note deleted.")
                    return
            except IndexError:
                pass

            await ctx.send("Note not found.")

    @_warnings.command("delete")
    async def warning_delete(self, ctx: commands.Context, warning_id: int):
        """Deletes warning

        Example:
        - `[p]warnings delete <warning id>`
        """
        async with self.config.guild(ctx.guild).warnings() as warnings:
            try:
                warning = warnings[warning_id - 1]
                if not warning["deleted"]:
                    # User must be an admin or owner of the warning
                    if not (warning["reporter"] == ctx.author.id or await is_admin_or_superior(self, ctx.author)):
                        await ctx.send("You don't have permission to do this.")
                        return

                    # Delete warning if not previously deleted
                    warning["deleted"] = True
                    await ctx.send("Warning deleted.")
                    return
            except IndexError:
                pass

            await ctx.send("Warning not found.")

    @_notes.command("list")
    async def notes_list(self, ctx: commands.Context, *, user: typing.Union[discord.Member, str] = None):
        """Lists notes and warnings for everyone or a specific user.

        Example:
        - `[p]notes list <user>`
        - `[p]notes list`
        """
        notes = []
        user_id = None
        if user is not None:
            user_id = user if isinstance(user, str) else user.id

        async with self.config.guild(ctx.guild).notes() as discord_notes:
            discord_notes = sorted(discord_notes, key=lambda x: x["date"], reverse=True)

            for note in discord_notes:
                if note["deleted"]:
                    # Ignore deleteds
                    continue
                if not (user is None or note["member"] == user_id):
                    # Ignore notes that don't relate to the target
                    continue

                member = None
                try:
                    member = ctx.guild.get_member(note["member"]) or note["member"]
                except Exception:
                    member = note["member"]

                modname = None
                try:
                    modname = ctx.guild.get_member(note["reporter"])
                    if modname:
                        modname = modname.name
                    else:
                        modname = note["reporterstr"] or note["reporter"]
                except Exception:
                    modname = note["reporterstr"] or note["reporter"]

                date = datetime.utcfromtimestamp(note["date"])
                display_time = date.strftime("%Y-%m-%d %H:%M:%SZ")
                notes.append(
                    f"📝#{note['id']} **{member} - Added by {modname}** " + f"- {display_time}\n " + f"{note['message']}"
                )

        warnings = []
        async with self.config.guild(ctx.guild).warnings() as discord_warnings:
            discord_warnings = sorted(discord_warnings, key=lambda x: x["date"], reverse=True)

            for warning in discord_warnings:
                if warning["deleted"]:
                    # Ignore deleteds
                    continue
                if not (user is None or warning["member"] == user_id):
                    # Ignore warnings that don't relate to the target
                    continue

                member = None
                try:
                    member = ctx.guild.get_member(warning["member"]) or warning["member"]
                except Exception:
                    member = warning["member"]

                modname = None
                try:
                    modname = ctx.guild.get_member(warning["reporter"])
                    if modname:
                        modname = modname.name
                    else:
                        modname = warning["reporterstr"] or warning["reporter"]
                except Exception:
                    modname = warning["reporterstr"] or warning["reporter"]

                date = datetime.utcfromtimestamp(warning["date"])
                display_time = date.strftime("%Y-%m-%d %H:%M:%SZ")
                warnings.append(
                    f"⚠️#{warning['id']} **{member} - Added by {modname}** " + f"- {display_time}\n " + f"{warning['message']}"
                )

        messages = "\n\n".join(warnings + notes)

        # Pagify implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/9698baf6e74f6b34f946189f05e2559a60e83706/redbot/core/utils/chat_formatting.py#L208
        pages = pagify(messages, shorten_by=58)
        embeds = []
        for page in pages:
            data = discord.Embed(colour=(await ctx.embed_colour()))
            if user is not None:
                data.title = f"Notes for {user} - {len(warnings)} " + f"warnings, {len(notes)} notes"
            else:
                data.title = f"All notes and warnings - {len(warnings)} " + f"warnings, {len(notes)} notes"
            data.description = page

            embeds.append(data)

        # Menu implementation
        # https://github.com/Cog-Creators/Red-DiscordBot/blob/d6f9ddc3afe00ac1e8b4925a73f6783a3f497b9e/redbot/core/utils/menus.py#L18
        if len(embeds) > 0:
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
        data = discord.Embed(colour=(await ctx.embed_colour()))
        data.title = "Notes Status"

        async with self.config.guild(ctx.guild).notes() as notes:
            data.add_field(name="Notes", value=f"{len(notes)} notes")

        async with self.config.guild(ctx.guild).warnings() as warnings:
            data.add_field(name="Warnings", value=f"{len(warnings)} warnings")
        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send("I need the `Embed links` permission to " + "send a notes status.")
