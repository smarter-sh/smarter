Example Manifests
=================

The Static plugin example is from the `plugins/static/ <https://github.com/smarter-sh/example-manifests/tree/main/plugins/static>`__ folder
of `smarter-sh/example-manifests <https://github.com/smarter-sh/example-manifests>`__, the
community-supported :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`,
which every Smarter platform loads when ``manage.py initialize_platform`` runs, and of which
``manage.py initialize_account`` gives each account its own copy. Its
`plugins/skill/ <https://github.com/smarter-sh/example-manifests/tree/main/plugins/skill>`__,
`plugins/websearch/ <https://github.com/smarter-sh/example-manifests/tree/main/plugins/websearch>`__ and
`plugins/image-search/ <https://github.com/smarter-sh/example-manifests/tree/main/plugins/image-search>`__ folders hold Skill, Websearch
and ImageSearch plugins. The API and SQL plugin examples are not part of it, and no platform
applies them: they are kept with this documentation, in
`docs/source/example-manifests/ <https://github.com/smarter-sh/smarter/tree/main/docs/source/example-manifests>`__,
for you to read and copy.

.. toctree::
   :maxdepth: 1

   example-manifests/api-plugin.rst
   example-manifests/sql-plugin.rst
   example-manifests/static-plugin.rst
