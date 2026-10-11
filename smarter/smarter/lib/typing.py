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
"""

from typing import Any, TypeAlias

SmarterDictType: TypeAlias = dict[str, Any]
"""
A mapping of string keys to values of any type.

E.g. keyword arguments, a status report, or a parsed YAML or JSON object whose
shape isn't modeled.
"""

__all__ = ["SmarterDictType"]
