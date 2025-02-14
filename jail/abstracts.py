import uuid
from abc import ABC, abstractmethod
from typing import List

import discord
from redbot.core import Config, commands


class JailABC(ABC):
    datetime: int
    channel_id: int
    role_id: int
    active: bool
    jailer: int
    user: int
    user_roles: List[int]
    archive_id: uuid.UUID

    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            # expected_type: type = self.__annotations__[key]
            # if not isinstance(val, expected_type):
            # raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)

    @classmethod
    @abstractmethod
    def new(
        cls,
        ctx: commands.Context,
        datetime: int,
        channel_id: int,
        role_id: int,
        active: bool,
        jailer: int,
        user: int,
        user_roles: List[int],
        uuid: uuid.UUID,
    ):
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


class JailSetABC(ABC):
    jails: List[JailABC]

    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            # expected_type: type = self.__annotations__[key]
            # if not isinstance(val, expected_type):
            # raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, jails: List[JailABC]):
        """Initialise the class in a command context"""
        pass

    @classmethod
    @abstractmethod
    def from_storage(cls, ctx: commands.Context, data: dict):
        """Initialise the class from a config record"""
        pass

    @abstractmethod
    def to_list(self) -> list:
        """Returns a list representation of the class, suitable for storing in config"""
        pass

    @abstractmethod
    def get_active_jail(self) -> JailABC:
        """Gets the current active jail in the set."""
        pass

    @abstractmethod
    def add_jail(self, jail: JailABC):
        """Saves a jail to the set."""
        pass


class JailConfigHelperABC(ABC):
    config: Config

    async def create_jail(self, ctx: commands.Context, datetime: int, member: discord.Member) -> JailABC:
        """Creates and saves a new jail."""
        pass

    async def get_jail_by_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> JailABC:
        """Returns a jail if one exists for the specified channel"""
        pass
