"""
Shared type aliases for the Smarter platform.

A type construction that the codebase spells out many times (more than about
ten) is declared here once, under a name with the ``Smarter`` prefix and the
``Type`` suffix, e.g. :data:`SmarterDictType`. Use these aliases instead of
repeating the construction, and wrap them at the point of use, e.g.
``Optional[SmarterDictType]`` or ``list[SmarterDictType]``.

An alias doesn't make a loose type acceptable. A mapping whose values really
can be anything is a :data:`SmarterDictType`, but a sizable, structured piece of
JSON still gets a Pydantic model (see ADR-031, Pydantic over JSON).

The module also has :func:`required`, which narrows an Optional value that is
never None in practice, e.g. a saved row's ``created_at``.
"""

from typing import Any, Optional, TypeAlias, TypeVar

SmarterDictType: TypeAlias = dict[str, Any]
"""
A mapping of string keys to values of any type.

E.g. keyword arguments, a status report, or a parsed YAML or JSON object whose
shape isn't modeled.
"""

_T = TypeVar("_T")


def required(value: Optional[_T], name: str) -> _T:
    """
    Return a value that is Optional in its type, but must not be None here.

    E.g. a saved row's ``created_at`` and ``updated_at``, which are nullable
    columns that Django sets on the first save, or an account's
    ``account_number``, which is generated when the account is created::

        status = SAMGuardrailStatus(
            accountNumber=required(self.account.account_number, "account.account_number"),
            created=required(guardrail.created_at, "guardrail.created_at"),
        )

    :param value: The value.
    :param name: What the value is, for the error message.
    :returns: The value.
    :raises ValueError: If the value is None.
    """
    if value is None:
        raise ValueError(f"{name} is None")
    return value


__all__ = ["SmarterDictType", "required"]
