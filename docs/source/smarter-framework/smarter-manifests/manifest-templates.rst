Manifest Templates
==================

Some built-in resources have to reach the platform that they run on, rather than a fixed host.
For example, the Smarter Project MCPClients read the Smarter Project MCP server of their own
platform, and the Stackademy ApiConnection queries that platform's Stackademy course catalogue. A
hard-coded host such as ``http://localhost:9357`` only works in local development.

Such a manifest is a template: a ``*.yaml.tpl`` file, which is a Python :class:`string.Template`
whose placeholders are filled in from ``smarter_settings`` when it is applied.

- ``${environment_platform_scheme}``: ``https``, or ``http`` in local development.
- ``${environment_platform_domain}``: e.g. ``alpha.platform.example.com``, or ``localhost:9357``
  in local development.

.. code-block:: yaml

    spec:
      connection:
        baseUrl: ${environment_platform_scheme}://${environment_platform_domain}

``manage.py load_from_github`` fills in the templates of the repository that it loads, e.g. the
``smarter_project*`` MCPClients of the :doc:`example manifests repository <example-manifests>` and
the Stackademy ApiConnection of the :doc:`Stackademy example project <stackademy>`, with
:func:`smarter.lib.manifest.template.render_manifest_template`.

.. automodule:: smarter.lib.manifest.template
   :members:
