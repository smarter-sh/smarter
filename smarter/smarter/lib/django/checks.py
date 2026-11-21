"""
Django system checks for Smarter's subclasses of Django's security middleware.

Django's deployment checks (``manage.py check --deploy``) look for its security middleware by its
dotted path: ``"django.middleware.security.SecurityMiddleware" in settings.MIDDLEWARE``. Smarter
installs subclasses instead, :class:`~smarter.apps.llmclient.middleware.security.SmarterSecurityMiddleware`
and :class:`~smarter.lib.django.middleware.csrf.SmarterCsrfViewMiddleware`, so Django reports them
missing (``security.W001`` and ``security.W003``, which ``SILENCED_SYSTEM_CHECKS`` silences), and it
skips every check that depends on them, e.g. ``SECURE_HSTS_SECONDS`` and ``CSRF_COOKIE_SECURE``.

:func:`check_security_middleware_subclasses` replaces those checks. For each of Django's security
middleware it finds a subclass in ``MIDDLEWARE``, and runs Django's own checks of its settings as if
Django's class were installed. Without a subclass it reports its own warning, so that removing one
is still noticed.
"""

from typing import Any, Callable, Optional

from django.conf import settings
from django.core.checks import CheckMessage, Tags, register
from django.core.checks import Warning as CheckWarning
from django.core.checks.security import base as security_checks
from django.core.checks.security import csrf as csrf_checks
from django.test.utils import override_settings
from django.utils.module_loading import import_string

SmarterCheckFunction = Callable[..., list[CheckMessage]]
"""A Django system check: it takes ``app_configs`` and keyword arguments, and returns its messages."""

SECURITY_MIDDLEWARE = "django.middleware.security.SecurityMiddleware"
"""The dotted path that Django's deployment checks look for, for its security middleware."""

CSRF_MIDDLEWARE = "django.middleware.csrf.CsrfViewMiddleware"
"""The dotted path that Django's deployment checks look for, for its CSRF middleware."""

GATED_CHECKS: dict[str, tuple[str, tuple[SmarterCheckFunction, ...]]] = {
    SECURITY_MIDDLEWARE: (
        "smarter.W001",
        (
            security_checks.check_sts,
            security_checks.check_sts_include_subdomains,
            security_checks.check_sts_preload,
            security_checks.check_content_type_nosniff,
            security_checks.check_ssl_redirect,
            security_checks.check_referrer_policy,
            security_checks.check_cross_origin_opener_policy,
        ),
    ),
    CSRF_MIDDLEWARE: (
        "smarter.W002",
        (csrf_checks.check_csrf_cookie_secure,),
    ),
}
"""
For each of Django's security middleware, the id of the warning that none of its subclasses is in.

``MIDDLEWARE``, and Django's checks that run only while it is installed.
"""


def middleware_subclass(base_path: str) -> Optional[str]:
    """
    Return the first entry of ``MIDDLEWARE`` whose class is ``base_path``'s class or a subclass of it.

    **Example:**

    >>> middleware_subclass("django.middleware.csrf.CsrfViewMiddleware")
    'smarter.lib.django.middleware.csrf.SmarterCsrfViewMiddleware'

    :param base_path: The dotted path of one of Django's middleware classes.
    :returns: The entry's dotted path, or None if no entry is that class or a subclass of it.
    """
    base_class = import_string(base_path)
    for path in settings.MIDDLEWARE:
        middleware_class = import_string(path)
        if isinstance(middleware_class, type) and issubclass(middleware_class, base_class):
            return path
    return None


@register(Tags.security, deploy=True)
def check_security_middleware_subclasses(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """
    Run Django's deployment checks of the settings that Smarter's security middleware subclasses read.

    Django runs these checks itself only when its own class's dotted path is in ``MIDDLEWARE``, so
    this check skips any middleware whose path is there. For a subclass, it runs them with Django's
    path appended to ``MIDDLEWARE``, and returns their messages, e.g. ``security.W004`` when
    ``SECURE_HSTS_SECONDS`` is not set. With neither, it returns a warning: ``smarter.W001`` for
    the security middleware, ``smarter.W002`` for the CSRF middleware.

    :param app_configs: The app configs to check, or None for all of them. Passed on to Django's checks.
    :param kwargs: Passed on to Django's checks.
    :returns: The messages of Django's checks, and the warnings of missing middleware.
    """
    messages: list[CheckMessage] = []
    for django_path, (warning_id, checks) in GATED_CHECKS.items():
        if django_path in settings.MIDDLEWARE:
            continue
        subclass = middleware_subclass(django_path)
        if subclass is None:
            messages.append(
                CheckWarning(
                    f"MIDDLEWARE has neither {django_path} nor a subclass of it.",
                    hint="Smarter installs its own subclass. See the MIDDLEWARE setting.",
                    id=warning_id,
                )
            )
            continue
        with override_settings(MIDDLEWARE=[*settings.MIDDLEWARE, django_path]):
            for check in checks:
                messages.extend(check(app_configs, **kwargs))
    return messages
