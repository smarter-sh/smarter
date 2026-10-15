The Extension's pyproject.toml
==============================

An Extension describes itself in the ``pyproject.toml`` at the root of its archive. It is not a
:doc:`SAM manifest <../smarter-manifests>`: it is a standard
`Python project file <https://packaging.python.org/en/latest/specifications/pyproject-toml/>`__:
Smarter reads its ``[project]`` table, and its own ``[tool.smarter]`` table. It is
validated by :class:`~smarter.apps.llmtool.extension.manifest.ExtensionManifest` when the
Extension is validated, packaged, published and installed.

``[project]``
-------------

.. list-table::
   :header-rows: 1
   :widths: 22 12 66

   * - Field
     - Required
     - Meaning
   * - ``name``
     - Yes
     - The distribution's name, by convention ``smarter-extension-<slug>``.
   * - ``version``
     - Yes
     - The version, a PEP 440 version such as ``1.2.0``. Released versions never change.
   * - ``description``
     - No
     - One line, shown in the admin console and the registry.
   * - ``authors``
     - No
     - ``[{ name = "...", email = "..." }]``. An uploaded Extension's publisher is its authors.
   * - ``license``
     - No
     - An SPDX expression, e.g. ``"AGPL-3.0"``, or the older ``{ text = "..." }`` table.
   * - ``requires-python``
     - No
     - The Python versions it works with, e.g. ``">=3.12"``.
   * - ``dependencies``
     - No
     - The libraries it imports, as PEP 508 requirements, e.g. ``"pandas>=2"``. They are checked
       against the platform's installed libraries, never installed.
   * - ``urls``
     - No
     - ``Homepage`` is shown in the registry.

Other ``[project]`` fields are allowed, and ignored.

``[tool.smarter]``
------------------

.. list-table::
   :header-rows: 1
   :widths: 22 12 66

   * - Field
     - Required
     - Meaning
   * - ``slug``
     - Yes
     - The Extension's permanent identifier: at most 32 lowercase letters and digits, in words
       separated by single hyphens, e.g. ``weather`` or ``date-calculator``.
   * - ``package``
     - Yes
     - The Python package, at the archive's root, that holds the code, e.g. ``weather``.
   * - ``display-name``
     - No
     - The name shown to people. Defaults to the slug in title case.
   * - ``requires-smarter``
     - No
     - The Smarter versions it works with, e.g. ``">=0.27,<1.0"``. Unreleased development builds
       satisfy every range.
   * - ``tools``
     - Yes
     - The tools' classes, as ``<module>:<class>``, in the package, e.g.
       ``["weather.tools:GetWeather"]``.
   * - ``lifecycle``
     - No
     - The class of its lifecycle hooks, as ``<module>:<class>``. See :doc:`lifecycle`.
   * - ``timeout``
     - No
     - Seconds that a tool call may run, from 1 to 300. Defaults to 30.
   * - ``icon``
     - No
     - The path of its icon, relative to the package, e.g. ``static/icon.svg``.
   * - ``settings``
     - No
     - The settings that an administrator configures: see below.
   * - ``switches``
     - No
     - The waffle switches that it owns: see :doc:`lifecycle`.

Settings
--------

Each ``[[tool.smarter.settings]]`` table declares one setting:

.. code-block:: toml

    [[tool.smarter.settings]]
    name = "weather_api_url"
    type = "url"
    default = "https://api.open-meteo.com/v1/forecast"
    description = "The Open-Meteo forecast api."

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Field
     - Meaning
   * - ``name``
     - A Python identifier. The tool reads the setting as ``context.settings.<name>``.
   * - ``type``
     - ``string`` (the default), ``integer``, ``float``, ``boolean``, ``url``, ``choice`` or
       ``secret``.
   * - ``description``
     - Shown to the administrator, in the settings form.
   * - ``default``
     - The value when none is configured. A secret has no default.
   * - ``required``
     - Whether the Extension can't be enabled until the setting has a value or a default.
   * - ``choices``
     - The allowed values of a ``choice`` setting.

A ``secret`` setting's value is a Smarter Secret, encrypted at rest. It reaches the tool as a
:class:`pydantic.SecretStr`. A setting that has neither a value nor a default is ``None``.

By convention, name a secret setting after the platform Secret that it would naturally use, such
as ``google_maps_api_key``: ``manage.py add_builtin_extensions`` configures an official
Extension's unset secret settings from the platform administrator's Secrets of the same names.

The Archive
-----------

An archive is a zip file that holds the ``pyproject.toml`` and the package, at its root, or all in
one top-level directory, as GitHub's source archives are. ``manage.py package_extension`` builds
one, with the README, LICENSE and CHANGELOG, if any, and without caches. An archive may be at most
10 MB, expand to at most 50 MB, and hold at most 2000 files, and may not contain links or paths
that leave its directory.

The package may hold:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Path
     - Purpose
   * - ``__init__.py``
     - Required. Its module docstring, in reStructuredText, is the Extension's documentation.
   * - ``manifests/*.yaml``
     - SAM manifests that the Extension applies when it is installed. See :doc:`lifecycle`.
   * - ``static/``
     - Assets, such as its icon.
   * - ``docs/*.rst`` or ``docs/*.md``
     - More documentation pages.
