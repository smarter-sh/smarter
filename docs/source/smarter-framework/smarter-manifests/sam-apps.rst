Resource Types' Feature Flags
=============================

Each Django app that owns SAM resource kinds, e.g. the guardrail app, which owns the Guardrail kind,
has a feature flag, ``smarter_settings.enable_<app>``, set with its ``SMARTER_ENABLE_<APP>``
environment variable. Every flag defaults to true. :data:`~smarter.lib.manifest.sam_apps.SAM_APPS` lists
the apps, their flags and their kinds. What an operator sees when a flag is false is in
:ref:`Turning resource types off <sam-app-feature-flags>`.

Code that serves an app's resources asks this module whether the app is on, rather than reading the
flag itself:

- a urlconf mounts each app's urls with :func:`~smarter.lib.manifest.sam_apps.sam_app_urlpatterns`, from
  a table of :class:`~smarter.lib.manifest.sam_apps.SamAppUrls`, e.g. ``SAM_APP_CONSOLE_URLS`` in
  :mod:`smarter.urls.console`;
- code that links to an app's page reverses it with
  :func:`~smarter.lib.manifest.sam_apps.reverse_if_enabled`, which returns None while the app is off;
- the cli api calls :func:`~smarter.lib.manifest.sam_apps.raise_if_kind_disabled` before it brokers a
  manifest, and the commands that apply manifests skip a kind for which
  :func:`~smarter.lib.manifest.sam_apps.kind_is_enabled` is false;
- each app's AppConfig names its flag in ``enabled_setting``. See
  :doc:`/smarter-framework/developer-reference/lib/django/apps`.

A new resource kind is added to its app's ``kinds`` in ``SAM_APPS``, or to ``CORE_KINDS`` if it belongs
to a core app. A test fails until it is in exactly one of them. A new SAM app gets an entry in
``SAM_APPS``, a flag in :class:`~smarter.common.conf.settings.features.FeatureSettings`, and a row in each
urlconf's table. Tests fail until it has all of them.

In a test, :func:`smarter.lib.unittest.sam_apps.disabled_sam_apps` turns flags off.

.. automodule:: smarter.lib.manifest.sam_apps
   :members:

System checks
-------------

.. automodule:: smarter.lib.manifest.checks
   :members:
