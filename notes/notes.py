"""discord red-bot notes"""

from __future__ import annotations

from typing import Optional

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

from .utils import MAYBE_MEMBER, ConfigHelper, NoteException


def invoked_warning_cmd(ctx: commands.Context) -> bool:
    """Useful for finding which alias triggered the command. Checks against the invoked parents attribute. Can only be used in subcommands."""
    return ctx.invoked_parents[0].startswith("warning")


class NotesCog(commands.Cog):
    """Notes Cog"""

    config: ConfigHelper

    def __init__(self):
        super().__init__()
        self.config = ConfigHelper()

    # Command groups

    @commands.guild_only()
    @checks.mod()
    @commands.group(name="notes", aliases=["note"])
    async def _notes(self, ctx: commands.Context):
        pass

    @commands.guild_only()
    @checks.mod()
    @commands.group(name="warnings", aliases=["warning"])
    async def _warnings(self, ctx: commands.Context):
        pass

    # Note commands

    @_notes.command("add")
    async def notes_add(
        self,
        ctx: commands.Context,
        user: MAYBE_MEMBER,
        *,
        message: str,
    ):
        """Log a note against a user."""
        note = await self.config.add_note(ctx, user, message, is_warning=False)
        await ctx.send(f"Note added (ID: {note.note_id}).")

    @_notes.command("delete")
    async def notes_delete(self, ctx: commands.Context, note_id: int):
        """Deletes a note."""
        try:
            await self.config.delete_note(ctx, note_id, is_warning=False)
            await ctx.send("Note deleted.")
        except NoteException as error_message:
            await ctx.send(str(error_message))

    @_notes.command("restore")
    async def notes_restore(self, ctx: commands.Context, note_id: int):
        """Restores a deleted note."""
        try:
            await self.config.restore_note(ctx, note_id, is_warning=False)
            await ctx.send("Note restored.")
        except NoteException as error_message:
            await ctx.send(str(error_message))

    # Warning commands

    @_warnings.command("add")
    async def warning_add(
        self,
        ctx: commands.Context,
        user: MAYBE_MEMBER,
        *,
        message: str,
    ):
        """Log a warning against a user."""
        note = await self.config.add_note(ctx, user, message, is_warning=True)
        await ctx.send(f"Warning added (ID: {note.note_id}).")

    @_warnings.command("delete")
    async def warning_delete(self, ctx: commands.Context, note_id: int):
        """Deletes a warning."""
        try:
            await self.config.delete_note(ctx, note_id, is_warning=True)
            await ctx.send("Warning deleted.")
        except NoteException as error_message:
            await ctx.send(str(error_message))

    @_warnings.command("restore")
    async def warning_restore(self, ctx: commands.Context, note_id: int):
        """Restores a deleted warning."""
        try:
            await self.config.restore_note(ctx, note_id, is_warning=True)
            await ctx.send("Warning restored.")
        except NoteException as error_message:
            await ctx.send(str(error_message))

    # General commands

    @checks.bot_has_permissions(embed_links=True)
    @_notes.command("list")
    async def notes_list(self, ctx: commands.Context, *, user: Optional[MAYBE_MEMBER] = None):
        """Lists notes and warnings for everyone or a specific user."""
        notes = await (self.config.get_notes_by_user(ctx, user) if user else self.config.get_all_notes(ctx))
        if not notes:
            return await ctx.send("No notes to display.")

        # Get number of notes and warnings
        num_notes = len([n for n in notes if not n.is_warning])
        num_warnings = len([n for n in notes if n.is_warning])

        # Convert to strings and pagify
        pages = list(pagify("\n\n".join(str(n) for n in notes)))

        # Create embeds from pagified data
        notes_target: Optional[str] = getattr(user, "display_name", str(user.id)) if user is not None else None
        base_embed_options = {
            "title": (
                (f"Notes for {notes_target}" if notes_target else "All notes")
                + f" - ({num_warnings} warnings, {num_notes} notes)"
            ),
            "colour": await ctx.embed_colour(),
        }
        embeds = [
            discord.Embed(**base_embed_options, description=page).set_footer(text=f"Page {index} of {len(pages)}")
            for index, page in enumerate(pages, start=1)
        ]

        if len(embeds) == 1:
            await ctx.send(embed=embeds[0])
        else:
            ctx.bot.loop.create_task(
                menu(ctx=ctx, pages=embeds, controls={"⬅️": prev_page, "⏹️": close_menu, "➡️": next_page}, timeout=180.0)
            )

    @checks.bot_has_permissions(embed_links=True)
    @_notes.command("status")
    async def notes_status(self, ctx: commands.Context):
        """
        Status of the cog.
        The bot will display how many notes it has recorded
        since it's inception.
        """
        all_notes = await self.config.get_all_notes(ctx)
        await ctx.send(
            embed=(
                discord.Embed(title="Notes Status", colour=await ctx.embed_colour())
                .add_field(name="Notes", value=str(len([n for n in all_notes if not n.is_warning])))
                .add_field(name="Warnings", value=str(len([n for n in all_notes if n.is_warning])))
            )
        )
