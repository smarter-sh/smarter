"""
Smarter enumeration helper classes.

:class:`SmarterEnumAbstract`, the base class of Smarter's enumerations, is defined in the
`smarter-types <https://docs.smarter-types.smarter.sh/>`__ package, which the platform and its Python
SDK share, and is re-exported here.
"""

from smarter_types import SmarterEnumAbstract


class SmarterEnum:
    """Smarter enumeration helper class."""

    @classmethod
    def all(cls) -> list[str]:
        """Return a list of all enumeration values."""
        return [
            value
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and name.isupper() and isinstance(value, str)
        ]

    @classmethod
    def list_all(cls) -> str:
        """Return a comma-separated string of all enumeration values."""
        return ", ".join(cls.all())

    def __str__(self) -> str:
        return str(self.value) if hasattr(self, "value") else super().__str__()  # type: ignore


class SmarterResourceOwnershipFilterEnum:
    """Enum-like class for ownership filter options."""

    OWNED = "owned"
    SHARED = "shared"
    ALL = "all"


__all__ = ["SmarterEnum", "SmarterEnumAbstract", "SmarterResourceOwnershipFilterEnum"]
