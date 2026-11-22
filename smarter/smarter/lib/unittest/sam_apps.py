"""
Turn SAM resource apps off in a test.

``smarter_settings`` is frozen, so a test can't set a flag on it. :func:`disabled_sam_apps` patches it
with a copy instead, in :mod:`smarter.common.conf`, which :mod:`smarter.lib.manifest.sam_apps` reads, and in
any module that imported it by name. Url patterns are built at import, so this doesn't unmount urls: see
:func:`smarter.lib.manifest.sam_apps.sam_app_urlpatterns` for those.
"""

from contextlib import ExitStack, contextmanager
from typing import Iterator
from unittest.mock import patch

from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings


@contextmanager
def disabled_sam_apps(*settings: str, modules: tuple[str, ...] = ()) -> Iterator[Settings]:
    """
    Patch ``smarter_settings`` with a copy whose flags are false.

    :param settings: The flags to turn off, e.g. ``app_guardrail_enable``.
    :param modules: The dotted names of more modules whose ``smarter_settings`` to patch, e.g.
        ``smarter.apps.api.web.session.views``.
    :returns: The patched copy of the settings.
    """
    update = {}
    for setting in settings:
        update[setting] = False
    settings_copy = smarter_settings.model_copy(update=update)
    with ExitStack() as stack:
        stack.enter_context(patch("smarter.common.conf.smarter_settings", settings_copy))
        for module in modules:
            stack.enter_context(patch(f"{module}.smarter_settings", settings_copy))
        yield settings_copy


__all__ = ["disabled_sam_apps"]
