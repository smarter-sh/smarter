"""
The base class of every Smarter Django app's ``AppConfig``.

Each app's ``apps.py`` declares what is particular to it, and :class:`SmarterAppConfig` does the rest:

.. code-block:: python

    class GuardrailConfig(SmarterAppConfig):
        name = "smarter.apps.guardrail"
        verbose_name = format_lazy("{} {}", SMARTER_APP_NAME, _("Guardrail"))
        enabled_setting = "enable_guardrail"

Its :meth:`~SmarterAppConfig.ready` imports the app's :attr:`~SmarterAppConfig.ready_modules`, which connects
their signal receivers, and logs that the app is ready. A SAM resource app whose feature flag is false, e.g.
``SMARTER_ENABLE_GUARDRAIL=false``, imports nothing and logs how to enable it. See
:mod:`smarter.lib.manifest.sam_apps`.
"""

import importlib
from typing import Optional

from django.apps import AppConfig

from smarter.common.conf import smarter_settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging
from smarter.lib.manifest.sam_apps import get_sam_app

logger = logging.getSmarterLogger(__name__)


class SmarterAppConfig(AppConfig):
    """
    A Smarter app's configuration: the modules that its :meth:`ready` imports, and its feature flag.

    It doesn't mix in :class:`~smarter.common.mixins.SmarterHelperMixin`, whose ``ready`` property would conflict
    with :meth:`ready`.
    """

    default = False
    """
    Django uses an ``apps.py``'s AppConfig only if it holds exactly one, not counting those whose ``default`` is.

    False. An app's ``apps.py`` imports this class too, so it isn't a default, and each subclass is
    (:meth:`__init_subclass__`).
    """

    def __init_subclass__(cls, **kwargs) -> None:
        """Make each app's subclass the default AppConfig of its ``apps.py``, which this class isn't."""
        super().__init_subclass__(**kwargs)
        cls.default = True

    enabled_setting: Optional[str] = None
    """
    The ``smarter_settings`` flag that enables a SAM resource app, e.g. ``enable_guardrail``, or None for a core app,.

    which is always enabled.
    """

    ready_modules: tuple[str, ...] = ("receivers", "signals")
    """
    The modules that :meth:`ready` imports, which connects their signal receivers.

    A name is relative to the app's
    package, e.g. ``receivers``, unless it is a dotted path from ``smarter.``, e.g. ``smarter.lib.django.checks``.
    """

    def is_enabled(self) -> bool:
        """
        Whether the app is enabled.

        :returns: The value of the app's feature flag, or True for a core app, which has none.
        """
        if self.enabled_setting is None:
            return True
        sam_app = get_sam_app(self.enabled_setting)
        return sam_app.is_enabled(smarter_settings)

    def ready_module_name(self, module: str) -> str:
        """
        Return the dotted path of one of :attr:`ready_modules`.

        :param module: The module's name, e.g. ``receivers`` or ``smarter.lib.django.checks``.
        :returns: Its dotted path, e.g. ``smarter.apps.guardrail.receivers``.
        """
        if module.startswith("smarter."):
            return module
        return f"{self.name}.{module}"

    def on_ready(self) -> None:
        """Do what is particular to the app, after its modules are imported.

        Does nothing, unless overridden.
        """

    def ready(self) -> None:
        """Import the app's modules, which connects their signal receivers, unless its feature flag is false."""
        app_title = str(self.verbose_name)
        if not self.is_enabled():
            sam_app = get_sam_app(str(self.enabled_setting))
            logger.info(
                "%s app is %s. Set env `%s=true` to enable.",
                app_title,
                SmarterReadyState.NOT_READY,
                sam_app.env_name,
            )
            return
        for module in self.ready_modules:
            module_name = self.ready_module_name(module)
            importlib.import_module(module_name)
        self.on_ready()
        logger.debug("%s app is %s", app_title, SmarterReadyState.READY)


__all__ = ["SmarterAppConfig"]
