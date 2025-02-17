# Credit to the Notes cog author(s) for this structure

from abc import ABC, abstractmethod
from typing import List, Optional

import discord
from redbot.core import Config, commands


# fixme: please use data classes
class BaseABC(ABC):
    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            # expected_type: type = self.__annotations__[key]
            # if not isinstance(val, expected_type):
            #     raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)


class TransferABC(BaseABC):
    prior: int
    reason: str
    to: int
    time: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, prior: int, reason: str, to: int, time: int):
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


class UseABC(BaseABC):
    user: int
    time: int

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, user: int, time: int):
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


class AliasABC(BaseABC):
    alias: str
    creator: int
    created: int
    tag: str
    uses: List[UseABC]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, alias: str, creator: int, created: int, tag: str, uses: List[UseABC]):  # noqa: PLR0913
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


class TagABC(BaseABC):
    tag: str
    creator: int
    owner: int
    created: int
    content: str
    transfers: List[TransferABC]
    uses: List[UseABC]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    @abstractmethod
    def new(cls, ctx: commands.Context, creator: int, owner: int, created: int, tag: str, content: str):  # noqa: PLR0913
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


class TagConfigHelperABC(ABC):
    config: Config

    async def log_uses(self, ctx: commands.Context) -> bool:
        """Returns whether to log tag/alias use."""
        pass

    async def set_log_uses(self, ctx: commands.Context, log: bool):
        """Sets whether to log tag/alias use."""
        pass

    async def log_transfers(self, ctx: commands.Context) -> bool:
        """Returns whether to log transfers."""
        pass

    async def set_log_transfers(self, ctx: commands.Context, log: bool):
        """Sets whether to log transfers."""
        pass

    async def create_tag(self, ctx: commands.Context, tag: str, content: str) -> TagABC:
        """Creates, saves, and returns a new Tag."""
        pass

    async def edit_tag(self, ctx: commands.Context, tag: str, content: str) -> TagABC:
        """Updates and saves the content of an existing tag."""
        pass

    async def transfer_tag(self, ctx: commands.Context, trigger: str, to: int, reason: str, time: int):
        """Transfers the specified tag ownership to the new specified owner and makes the transfer entry."""
        pass

    async def get_tag(self, ctx: commands.Context, tag: str) -> TagABC:
        """Returns the tag, if any, for the given key."""
        pass

    async def get_tag_by_alias(self, ctx: commands.Context, alias: AliasABC) -> TagABC:
        """Returns the associated tag for the given alias."""
        pass

    async def get_tags(self, ctx: commands.Context, creator: Optional[discord.User]) -> List[TagABC]:
        """Returns a list of all tags, or those created by the specified user if provided."""
        pass

    async def get_tags_by_owner(self, ctx: commands.Context, owner_id: int) -> List[TagABC]:
        """Returns a list of tags owned by the provided owner."""
        pass

    async def get_tag_or_alias(self, ctx: commands.Context, trigger: str) -> (TagABC, AliasABC):
        """For the given trigger: returns the tag and no alias if a tag, the resolved tag plus alias if an alias, and
        none if neither."""
        pass

    async def add_tag_use(self, ctx: commands.Context, tag: TagABC, user: int, time: int):
        """Adds and saves a usage entry for the specified tag."""
        pass

    async def create_alias(self, ctx: commands.Context, alias: str, tag: str, creator: int, created: int):
        """Creates and saves the specified alias for the tag."""
        pass

    async def delete_alias(self, ctx: commands.Context, alias: str):
        """Deletes the specified alias and related data."""
        pass

    async def get_alias(self, ctx: commands.Context, alias: str) -> AliasABC:
        """Returns the alias, if any, for the given key."""
        pass

    async def get_aliases(self, ctx: commands.Context, creator: Optional[discord.User]) -> List[AliasABC]:
        """Returns a list of all aliases, or those created by the specified user if provided."""
        pass

    async def get_aliases_by_tag(self, ctx: commands.Context, tag: TagABC) -> List[AliasABC]:
        """Returns a list of aliases for the given tag."""
        pass

    async def get_aliases_by_owner(self, ctx: commands.Context, owner_id: int) -> List[AliasABC]:
        """Returns a list of aliases owned by the provided owner."""
        pass

    async def add_alias_use(self, ctx: commands.Context, alias: AliasABC, user: int, time: int):
        """Adds and saves a usage entry for the specified alias and its associated tag."""
        pass
