"""Extensions to Django's built-in shortcuts."""

from typing import Optional

from django.urls import reverse as django_reverse

from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


def reverse(*args, urlconf: Optional[str] = None, **kwargs) -> str:
    """
    Convert a series of namespaces and a view name into a URL path.

    This is a wrapper around
    Django's built-in ``reverse`` function, but it is designed to fit
    the exact pattern used across the Smarter codebase, which is to pass
    in a series of namespace arguments followed by a view name.

    The result is deliberately not cached in Redis. A URL path comes from
    the deployed URLconf, so a shared cache that outlives a deployment
    keeps serving the paths of the previous release after a route moves.
    Django's resolver already caches its reverse lookups in each process.

    For example, if you have a view named "my_view" that is in the "my_app"
    namespace, you would call this function like this:

    .. code-block:: python

        reverse("my_app:my_view")
        reverse("my_app", "my_view")

    This function joins the arguments with ``:`` and passes the view name to
    Django's ``reverse`` function.

    Pass ``urlconf`` to reverse against a particular URLconf rather than the
    one that django-hosts activated for the current request. Code that builds
    web console links on every request, such as a context processor, passes
    ``settings.ROOT_URLCONF``, because a deployed LLMClient's host is served by
    :mod:`smarter.urls.llmclients`, which has none of the console's names.

    :param args: A series of strings representing namespaces and the view name. If any of them
        is not a string, all arguments are passed to Django's ``reverse`` unchanged.
    :param urlconf: The dotted path of the URLconf to reverse against. Defaults to the active one.
    :param kwargs: Any keyword arguments to pass to Django's ``reverse`` function. If any keyword
        arguments are provided, this function assumes that the caller is not using the expected
        pattern, and passes all arguments directly to Django's ``reverse`` function.
    :returns: The URL path corresponding to the given view name and namespaces.
    :raises django.urls.NoReverseMatch: if no url pattern has the view name.
    """
    if kwargs:
        # not our pattern, so just pass through to Django's reverse function
        return django_reverse(*args, urlconf=urlconf, **kwargs)

    for arg in args:
        if not isinstance(arg, str):
            # not our pattern, so just pass through to Django's reverse function
            return django_reverse(*args, urlconf=urlconf, **kwargs)

    # each argument is a view name or namespaces, e.g. "namespace1:namespace2:view_name".
    reverse_path = ":".join(args)
    retval = django_reverse(reverse_path, urlconf=urlconf)
    logger.debug(
        "%s.reverse() view name %s resolved to path %s",
        logger_prefix,
        reverse_path,
        retval,
    )
    return retval


__all__ = ["reverse"]
