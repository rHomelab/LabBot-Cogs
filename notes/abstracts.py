from abc import ABC, abstractmethod
from typing import Callable, Iterable, List, Union

import discord
from redbot.core import Config, commands

MAYBE_MEMBER = Union[discord.Member, discord.Object]

# fixme: please use data classes


class NoteABC(ABC):
    """Represents a note record"""

    note_id: int
    member_id: int
    message: str
    reporter_id: int
    reporter_name: str
    created_at: int
    deleted: bool
    is_warning: bool
    _guild: discord.Guild

    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            expected_type: type = self.__annotations__[key]
            if not isinstance(val, expected_type):
                raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, note_id: int, member_id: int, message: str, *, is_warning: bool = False):
        """Initialise the class in a command context"""
        pass

    @classmethod
    @abstractmethod
    def from_storage(cls, ctx: commands.Context, data: dict, *, is_warning: bool = False):
        """Initialise the class from a config record"""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """The string representation of the class. Used primarily in message embeds"""
        pass

    @abstractmethod
    def __lt__(self, other) -> bool:
        """Important for chronological sorting. Compares the created_at attribute of the instances"""
        pass

    @abstractmethod
    def delete(self):
        """Sets the deleted value to True"""
        pass

    @abstractmethod
    def undelete(self):
        """Sets the deleted value to False"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Returns a dictionary representation of the class, suitable for storing in config"""
        pass


class ConfigHelperABC(ABC):
    config: Config

    @staticmethod
    @abstractmethod
    def filter_not_deleted(note: NoteABC) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def filter_match_user_id(user_id: int) -> Callable[[NoteABC], bool]:
        pass

    @abstractmethod
    def sorted_notes(self, notes: Iterable[NoteABC]) -> List[NoteABC]:
        """Sorts notes by creation date"""
        pass

    @abstractmethod
    async def add_note(self, ctx: commands.Context, member_id: int, message: str, *, is_warning: bool) -> NoteABC:
        pass

    @abstractmethod
    async def get_all_notes(self, ctx: commands.Context) -> List[NoteABC]:
        pass

    @abstractmethod
    async def get_notes_by_user(self, ctx: commands.Context, user: MAYBE_MEMBER) -> List[NoteABC]:
        pass

    @abstractmethod
    async def delete_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool):
        pass

    @abstractmethod
    async def restore_note(self, ctx: commands.Context, note_id: int, *, is_warning: bool):
        pass
