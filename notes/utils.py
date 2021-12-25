from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, Union

import discord
from redbot.core import Config, commands

from .abstracts import ConfigHelperABC, NoteABC

MAYBE_MEMBER = Union[discord.Member, discord.Object]


class NoteException(Exception):
    pass


class Note:
    note_id: int
    member_id: int
    message: str
    reporter_id: int
    reporter_name: str
    created_at: float
    deleted: bool
    is_warning: bool
    _guild: discord.Guild

    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            expected_type: type = self.__annotations__[key]
            if isinstance(expected_type, str):
                raise TypeError("For some reason all the values of the annotations dictionary have been turned into fucking strings. Everything's fucked, we should've never tricked sand into thinking")
            if not isinstance(val, expected_type):
                raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)

    @classmethod
    def new(cls, ctx: commands.Context, note_id: int, member_id: int, message: str, *, is_warning: bool = False):
        return cls(
            note_id=note_id,
            member_id=member_id,
            message=message,
            reporter_id=ctx.author.id,
            reporter_name=ctx.author.name,
            created_at=datetime.utcnow().timestamp(),
            deleted=False,
            is_warning=is_warning,
            _guild=ctx.guild
        )

    @classmethod
    def from_storage(cls, ctx: commands.Context, data: dict, *, is_warning: bool = False) -> Note:
        return cls(
            note_id=data["id"],
            member_id=data["member"],
            message=data["message"],
            reporter_id=data["reporter"],
            reporter_name=data["reporterstr"],
            created_at=data["date"],
            deleted=data["deleted"],
            is_warning=is_warning,
            _guild=ctx.guild
        )

    def __str__(self) -> str:
        icon = "\N{WARNING SIGN}" if self.is_warning else "\N{MEMO}"
        member_name = self._guild.get_member(self.member_id) or self.member_id
        reporter_name = self._guild.get_member(self.reporter_id) or self.reporter_name
        return f"{icon} #{self.note_id} **{member_name} - Added by {reporter_name}** - <t:{int(self.created_at)}:f>\n{self.message}"

    def __lt__(self, other: Note) -> bool:
        return self.created_at < other.created_at

    def delete(self) -> Note:
        self.deleted = True
        return self

    def undelete(self) -> Note:
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
            "deleted": self.deleted
        }


class ConfigHelper(ConfigHelperABC):

    def __init__(self):
        self.config = Config.get_conf(None, identifier=127318281, cog_name="NotesCog")
        self.config.register_guild(notes=[], warnings=[])

    @staticmethod
    def filter_not_deleted(note: Note) -> bool: return not note.deleted

    @staticmethod
    def filter_match_user_id(user_id: int) -> Callable[[Note], bool]:
        def predicate(note: Note) -> bool:
            return note.member_id == user_id

        return predicate

    @staticmethod
    def sort_by_date_and_warning(note: Note) -> float:
        return note.created_at * (int(note.is_warning) + 1)

    def sorted_notes(self, notes: Iterable[Note]) -> list[Note]:
        return sorted(
            filter(self.filter_not_deleted, notes),
            key=self.sort_by_date_and_warning
        )

    async def add_note(self, ctx: commands.Context, user: MAYBE_MEMBER, message: str, *, is_warning: bool = False):
        async with getattr(self.config.guild(ctx.guild), "warnings" if is_warning else "notes")() as notes:
            notes.append(Note.new(
                ctx,
                len(notes) + 1,
                user.id,
                message,
                is_warning=is_warning
            ).to_dict())

    async def get_all_notes(self, ctx: commands.Context) -> list[Note]:
        config_group = self.config.guild(ctx.guild)
        notes = [Note.from_storage(ctx, data) for data in await config_group.notes()]
        warnings = [Note.from_storage(ctx, data, is_warning=True) for data in await config_group.warnings()]
        return self.sorted_notes(notes + warnings)

    async def get_notes_by_user(self, ctx: commands.Context, user: MAYBE_MEMBER) -> list[Note]:
        config_group = self.config.guild(ctx.guild)
        notes = [Note.from_storage(ctx, data) for data in await config_group.notes()]
        warnings = [Note.from_storage(ctx, data, is_warning=True) for data in await config_group.warnings()]
        return self.sorted_notes(filter(self.filter_match_user_id(user.id), notes + warnings))

    async def delete_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool = False):
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

    async def restore_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool = False):
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
