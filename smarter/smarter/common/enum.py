"""Smarter enumeration base helper class."""

from enum import Enum


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all_values(cls) -> list[str]:
        retval = [member.value for name, member in cls.__members__.items() if not name.startswith("_")]
        return retval

    def __str__(self) -> str:
        return self.value
