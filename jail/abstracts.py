from abc import ABC
from typing import List

from redbot.core import Config


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


class JailABC(ABC):

    datetime: int
    channel_id: int
    jailer: int
    user: int
    user_roles: List[str]
    messages: List[MessageABC]

    def __init__(self, **kwargs):
        if kwargs.keys() != self.__annotations__.keys():
            raise Exception("Invalid kwargs provided")

        for key, val in kwargs.items():
            expected_type: type = self.__annotations__[key]
            if not isinstance(val, expected_type):
                raise TypeError(f"Expected type {expected_type} for kwarg {key!r}, got type {type(val)} instead")

            setattr(self, key, val)


class JailConfigHelperABC(ABC):
    config: Config
