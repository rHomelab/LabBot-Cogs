from __future__ import annotations


class LoggingConfiguration:
    VALID_FLAGS = {
        "on_tag_create": 0,
        "on_tag_delete": 1,
        "on_tag_transfer": 2,
        "on_tag_edit": 3,
        "on_tag_rename": 4,
        "on_tag_alias_create": 5,
        "on_tag_alias_delete": 6,
    }

    _value = 0

    def __init__(self, value: int = 0):
        self._value = value

    def get(self, key: str) -> bool:
        """Fetch the boolean value of a flag"""
        flag_value: int = 1 << self.VALID_FLAGS[key]
        return self._value & flag_value == flag_value

    def set(self, key: str, value: bool):
        """Set a flag value to True or False"""
        if value:  # Set flag to true
            self._value = self._value | (1 << self.VALID_FLAGS[key])
        else:  # Set flag to false
            self._value = self._value ^ (1 << self.VALID_FLAGS[key])

    def update(self, **kwargs: bool):
        """Bulk update flags"""
        for key, value in kwargs.items():
            self.set(key, value)

    @classmethod
    def all(cls) -> LoggingConfiguration:
        obj = cls()
        obj.update(**{key: True for key in cls.VALID_FLAGS})
        return obj

    def to_int(self) -> int:
        return self._value
