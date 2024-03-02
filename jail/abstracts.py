from abc import ABC, abstractmethod
from typing import List

import discord
from redbot.core import Config, commands


class EditABC(ABC):
    datetime: int
    content: str

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
    def new(cls, ctx: commands.Context, datetime: int, content: str):
        """Initialise the class in a command context"""
        pass

    @classmethod
    @abstractmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        """Initialise the class from a config record"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Returns a dictionary representation of the class, suitable for storing in config"""
        pass


class MessageABC(ABC):
    datetime: int
    author: int
    deleted: bool
    deleted_datetime: int
    content: str
    edits: List[EditABC]

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
    def new(cls, ctx: commands.Context, datetime: int, author: int, deleted: bool, deleted_datetime: int,
            content: str, edits: List[EditABC]):
        """Initialise the class in a command context"""
        pass

    @classmethod
    @abstractmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        """Initialise the class from a config record"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Returns a dictionary representation of the class, suitable for storing in config"""
        pass


class JailABC(ABC):
    datetime: int
    channel_id: int
    role_id: int
    active: bool
    jailer: int
    user: int
    user_roles: List[int]
    messages: List[MessageABC]

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
    def new(cls, ctx: commands.Context, datetime: int, channel_id: int, role_id: int, active: bool, jailer: int,
            user: int, user_roles: List[int], messages: List[MessageABC]):
        """Initialise the class in a command context"""
        pass

    @classmethod
    @abstractmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        """Initialise the class from a config record"""
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """Returns a dictionary representation of the class, suitable for storing in config"""
        pass


class JailConfigHelperABC(ABC):
    config: Config

    async def create_jail(self, ctx: commands.Context, datetime: int, member: discord.Member) -> JailABC:
        """Creates and saves a new jail."""
        pass

    async def get_jail_by_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> JailABC:
        """Returns a jail if one exists for the specified channel"""
        pass
