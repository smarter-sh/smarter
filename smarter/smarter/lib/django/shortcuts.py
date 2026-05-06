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

    For example, if you have a view named "my_view" that is in the "my_app"
    namespace, you would call this function like this:

    ```python
    reverse("my_app:my_view")
    ```

    This function will then split the argument into its components and pass
    them to Django's `reverse` function in the correct format.

    param args: A series of strings representing namespaces and the view name.
    param kwargs: Any keyword arguments to pass to Django's `reverse` function. If any keyword arguments are provided, this function will assume that the caller is not using the expected pattern and will pass all arguments directly to Django's `reverse` function without modification.
    return: The URL path corresponding to the given view name and namespaces.
    rtype: str
    """
    if kwargs:
        # not our pattern, so just pass through to Django's reverse function
        return django_reverse(*args, **kwargs)

    path_parts = []
    for arg in args:
        if not isinstance(arg, str):
            # not our pattern, so just pass through to Django's reverse function
            return django_reverse(*args, **kwargs)

        # unpack namespaces and view name from the argument, which is expected to be in the format "namespace1:namespace2:view_name"
        path_parts.append(arg.split(":"))

    reverse_path = ":".join([item for sublist in path_parts for item in sublist])
    retval = django_reverse(reverse_path)
    logger.debug(
        "%s.reverse() view name %s resolved to path %s",
        logging.formatted_text(__name__),
        reverse_path,
        retval,
    )
    return retval


__all__ = ["reverse"]
