Apps
====

Every Smarter Django app's ``AppConfig`` subclasses
:class:`~smarter.lib.django.apps.SmarterAppConfig`. An app's ``apps.py`` declares only its dotted
name and its name in the Django admin, both from its ``const.py``, and, for a SAM resource app, its
feature flag. The app's ``presentation_app_name`` is marked with ``gettext_noop`` in ``const.py``, and
translated where it is shown, so the Django admin shows the app's name in the user's language.

.. code-block:: python

    from django.utils.text import format_lazy
    from django.utils.translation import gettext_lazy as _

    from smarter.common.conf import smarter_settings
    from smarter.lib.django.apps import SmarterAppConfig

    from .const import namespace, presentation_app_name


    class GuardrailConfig(SmarterAppConfig):
        name = f"smarter.apps.{namespace}"
        verbose_name = format_lazy("{} {}", smarter_settings.platform_branding_app_name, _(presentation_app_name))
        enabled_setting = "app_guardrail_enable"

Its ``ready()`` imports the app's ``receivers`` and ``signals`` modules, or the
``ready_modules`` that the app names, and logs that the app is ready. If the app's feature flag is
false, it imports nothing, so none of its receivers are connected, and logs the environment variable
that turns it on. An app that has more to do once it is ready overrides ``on_ready()``. See
:doc:`/smarter-framework/smarter-manifests/sam-apps`.

.. automodule:: smarter.lib.django.apps
   :members:
