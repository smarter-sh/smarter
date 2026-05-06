"""
Extensions to Django's built-in shortcuts.
"""

from django.urls import reverse as django_reverse

from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)


def reverse(*args, **kwargs) -> str:
    """
    Converts a series of args into a URL path. This is a wrapper around
    Django's built-in `reverse` function, but it is designed to to fit
    the exact pattern used across the Smarter codebase, which is to pass
    in a series of namespace arguments followed by a view name.
    """
    if kwargs:
        # not our pattern, so just pass through to Django's reverse function
        logger.warning(
            "%s.reverse() was called with kwargs, which is outside of the expected pattern. Passing through to Django's reverse function.",
            logging.formatted_text(__name__),
        )
        return django_reverse(*args, **kwargs)

    path_parts = []
    for arg in args:
        if not isinstance(arg, str):
            # not our pattern, so just pass through to Django's reverse function
            logger.warning(
                "%s.reverse() was called with a non-string argument, which is outside of the expected pattern. Passing through to Django's reverse function.",
                logging.formatted_text(__name__),
            )
            return django_reverse(*args, **kwargs)

        # unpack namespaces and view name from the argument, which is expected to be in the format "namespace1:namespace2:view_name"
        path_parts.append(arg.split(":"))

    return django_reverse(":".join([item for sublist in path_parts for item in sublist]))


__all__ = ["reverse"]
