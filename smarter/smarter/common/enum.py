"""Smarter enumeration base helper class."""

from enum import Enum


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all(cls) -> list[str]:
        retval = [member.value for name, member in cls.__members__.items() if not name.startswith("_")]
        return retval

    @classmethod
    def list_all(cls) -> str:
        return ", ".join(cls.all())

    def __str__(self) -> str:
        return self.value


class SmarterEnum:
    """Smarter enumeration helper class."""

    @classmethod
    def all(cls) -> list[str]:
        return [
            value
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and name.isupper() and isinstance(value, str)
        ]

    @classmethod
    def list_all(cls) -> str:
        return ", ".join(cls.all())

    def __str__(self) -> str:
        return self.value
