from datetime import datetime
from typing import Callable, Iterable, List, Union

import discord
from redbot.core import Config, commands

from .abstracts import ConfigHelperABC, NoteABC

MAYBE_MEMBER = Union[discord.Member, discord.Object]


class NoteException(Exception):
    pass


class Note(NoteABC):
    @classmethod
    def new(cls, ctx: commands.Context, note_id: int, member_id: int, message: str, *, is_warning: bool = False):
        return cls(
            note_id=note_id,
            member_id=member_id,
            message=message,
            reporter_id=ctx.author.id,
            reporter_name=ctx.author.name,
            created_at=int(datetime.utcnow().timestamp()),
            deleted=False,
            is_warning=is_warning,
            _guild=ctx.guild,
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict, *, is_warning: bool = False):
        return cls(
            note_id=data["id"],
            member_id=int(data["member"]),  # FIXME: Migrate all stored values to int
            message=data["message"],
            reporter_id=data["reporter"],
            reporter_name=data["reporterstr"],
            created_at=int(data["date"]),  # FIXME: Migrate all stored values to int
            deleted=data["deleted"],
            is_warning=is_warning,
            _guild=ctx.guild,
        )

    def __str__(self) -> str:
        icon = "\N{WARNING SIGN}" if self.is_warning else "\N{MEMO}"
        member_name = self._guild.get_member(self.member_id) or self.member_id
        reporter_name = self._guild.get_member(self.reporter_id) or self.reporter_name
        return f"{icon} #{self.note_id} **{member_name} - Added by {reporter_name}** - <t:{int(self.created_at)}:f>\n{self.message}"

    def __lt__(self, other) -> bool:
        return self.created_at < other.created_at

    def delete(self):
        self.deleted = True
        return self

    def undelete(self):
        self.deleted = False
        return self

    def to_dict(self) -> dict:
        return {
            "id": self.note_id,
            "member": self.member_id,
            "message": self.message,
            "reporter": self.reporter_id,
            "reporterstr": self.reporter_name,
            "date": self.created_at,
            "deleted": self.deleted,
        }


class ConfigHelper(ConfigHelperABC):
    def __init__(self):
        self.config = Config.get_conf(None, identifier=127318281, cog_name="NotesCog")
        self.config.register_guild(notes=[], warnings=[])

    @staticmethod
    def filter_not_deleted(note: Note) -> bool:
        return not note.deleted

    @staticmethod
    def filter_match_user_id(user_id: int) -> Callable[[Note], bool]:
        def predicate(note: Note) -> bool:
            return note.member_id == user_id

        return predicate

    def sorted_notes(self, notes: Iterable[Note]) -> List[Note]:
        return sorted(filter(self.filter_not_deleted, notes), key=lambda note: note.created_at)

    async def add_note(self, ctx: commands.Context, user: MAYBE_MEMBER, message: str, *, is_warning: bool) -> Note:
        note = None
        async with getattr(self.config.guild(ctx.guild), "warnings" if is_warning else "notes")() as notes:
            note = Note.new(ctx, len(notes) + 1, user.id, message, is_warning=is_warning)
            notes.append(note.to_dict())
        return note

    async def get_all_notes(self, ctx: commands.Context) -> List[Note]:
        config_group = self.config.guild(ctx.guild)
        notes = [Note.from_storage(ctx, data) for data in await config_group.notes()]
        warnings = [Note.from_storage(ctx, data, is_warning=True) for data in await config_group.warnings()]
        return self.sorted_notes(warnings + notes)

    async def get_notes_by_user(self, ctx: commands.Context, user: MAYBE_MEMBER) -> List[Note]:
        config_group = self.config.guild(ctx.guild)
        notes = [Note.from_storage(ctx, data) for data in await config_group.notes()]
        warnings = [Note.from_storage(ctx, data, is_warning=True) for data in await config_group.warnings()]
        return self.sorted_notes(filter(self.filter_match_user_id(user.id), notes + warnings))

    async def delete_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool):
        async with getattr(self.config.guild(ctx.guild), "warnings" if is_warning else "notes")() as notes:
            try:
                note = Note.from_storage(ctx, notes[note_id - 1], is_warning=is_warning)
            except IndexError:
                raise NoteException(f"Note with ID {note_id} could not be found.")

            if note.member_id == ctx.author.id:
                raise NoteException("You cannot manage this note.")

            if note.deleted:
                raise NoteException("Note already deleted.")

            notes[note.note_id - 1] = note.delete().to_dict()

    async def restore_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool):
        async with getattr(self.config.guild(ctx.guild), "warnings" if is_warning else "notes")() as notes:
            try:
                note = Note.from_storage(ctx, notes[note_id - 1], is_warning=is_warning)
            except IndexError:
                raise NoteException(f"Note with ID {note_id} could not be found.")

            if note.member_id == ctx.author.id:
                raise NoteException("You cannot manage this note.")

            if not note.deleted:
                raise NoteException("Note not already deleted.")

            notes[note.note_id - 1] = note.undelete().to_dict()
