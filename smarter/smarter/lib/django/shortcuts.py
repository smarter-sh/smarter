"""
Extensions to Django's built-in shortcuts.
"""

from django.urls import reverse as django_reverse


def reverse(*args) -> str:
    """
    Converts a series of args into a URL path. This is a wrapper around
    Django's built-in `reverse` function, but it is designed to to fit
    the exact pattern used across the Smarter codebase, which is to pass
    in a series of namespace arguments followed by a view name.
    """
    path_parts = []
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError(
                f"All arguments to smarter.lib.django.shortcuts.reverse must be strings. Received argument of type {type(arg)}: {arg}"
            )

        # unpack namespaces and view name from the argument, which is expected to be in the format "namespace1:namespace2:view_name"
        path_parts.append(arg.split(":"))

    return django_reverse(":".join([item for sublist in path_parts for item in sublist]))
