"""Smarter enumeration base helper class."""

from enum import Enum


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all_values(cls) -> list[str]:
        return [member.value for name, member in cls.__members__.items() if not name.startswith("_")]
