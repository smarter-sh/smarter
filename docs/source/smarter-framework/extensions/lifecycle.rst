The Extension Lifecycle
=======================

An Extension is installed, configured, enabled, updated, rolled back, disabled and uninstalled by
a platform administrator. Most of what an Extension needs at each step is declared, and the
platform does it: settings, waffle switches, and SAM resources. For anything else, an Extension
has lifecycle hooks.

Waffle Switches
---------------

An Extension can own `waffle <https://waffle.readthedocs.io/>`__ switches, which an administrator
turns on and off in the admin console, for example to log more, or to try a new behavior:

.. code-block:: toml

    [[tool.smarter.switches]]
    name = "verbose"
    description = "Adds the forecast's raw response to the logs."
    default = false

The switch is created as ``ext_<slug>_<name>``, with the slug's hyphens as underscores, e.g.
``ext_weather_verbose``, when the Extension is installed, and deleted when it is uninstalled. A tool
reads it with ``context.switch_is_active("verbose")``.

SAM Resources
-------------

An Extension can create Smarter resources, such as a Secret or a Plugin, by shipping their
manifests in its package's ``manifests/`` directory. They are applied, in filename order, through
the same brokers as ``smarter apply``, and owned by the platform's administrator. Prefix their
names with the Extension's slug, so that they don't collide with anyone else's.

Smarter records each resource it creates. Uninstalling the Extension deletes them; an update
applies the new version's SAM manifests, and deletes the resources that the new version no longer
ships.

Hooks
-----

For anything that isn't declared, name a subclass of
:class:`~smarter.apps.llmtool.extension.lifecycle.SmarterExtensionLifecycle` in ``pyproject.toml``:

.. code-block:: toml

    [tool.smarter]
    lifecycle = "weather.lifecycle:Lifecycle"

and override the hooks you need. Every hook does nothing by default:

.. code-block:: python
    :caption: weather/lifecycle.py

    """The weather extension's lifecycle hooks."""

    from smarter.apps.llmtool.extension import LifecycleContext, SmarterExtensionLifecycle


    class Lifecycle(SmarterExtensionLifecycle):
        """Warn when the forecast api changes between versions."""

        def pre_upgrade(self, context: LifecycleContext) -> None:
            if context.previous_version and context.previous_version.startswith("0."):
                context.logger.warning("weather 1.0 uses the Open-Meteo v1 api: check weather_api_url")

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Hook
     - When it runs
   * - ``pre_install``
     - Before a new Extension is saved. Raise to cancel the install.
   * - ``post_install``
     - After it is installed, its switches created and its SAM manifests applied.
   * - ``pre_upgrade``
     - From the new version's code, before it replaces ``context.previous_version``, on an update
       or a rollback. Raise to cancel.
   * - ``post_upgrade``
     - From the new version's code, after it replaced ``context.previous_version``.
   * - ``on_enable``
     - When an administrator enables it. Raise to keep it disabled.
   * - ``on_disable``
     - When an administrator disables it.
   * - ``pre_uninstall``
     - Before it is uninstalled. Raise to cancel the uninstall.
   * - ``post_uninstall``
     - After its resources and switches are deleted, just before its rows are.

Each hook receives a :class:`~smarter.apps.llmtool.extension.lifecycle.LifecycleContext`, with the
Extension, its version and previous version, its settings, the platform administrator's profile,
which owns what it creates, and a logger. ``context.apply_manifest(yaml)`` applies a SAM manifest
and records it, so that uninstalling deletes it, and ``context.delete_resource(kind, name)``
deletes one.

The Rules
~~~~~~~~~

- Hooks run once per cluster, in the process that carries out the administrator's action, not in
  every pod.
- A ``pre_*`` hook that raises cancels the action, and nothing changes.
- A ``post_*`` hook that raises leaves the Extension installed but disabled, with the error shown
  on its admin page.
- ``on_disable`` and ``post_uninstall`` can't cancel anything: their errors are logged.

How Code Is Loaded
------------------

The platform runs in many processes, in many pods, which start and stop. An installed version's
archive is stored in the database, and each process extracts and imports it the first time it
needs it. Each version is imported under a name of its own, so an update imports the new version
beside the old one, and tool calls that are running finish on the old code. This is why an
Extension's modules must import each other with relative imports, and why they should do no work
when they are imported.
