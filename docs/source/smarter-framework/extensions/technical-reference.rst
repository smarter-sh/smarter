Technical Reference
===================

The Extension framework is the ``smarter.apps.llmtool.extension`` package, and its models are in
``smarter.apps.llmtool.models.extension``. An Extension's code imports only the public classes of
:mod:`smarter.apps.llmtool.extension`: the tool protocol, the lifecycle hooks, and the testing
helpers. The rest is how the platform installs, loads and runs Extensions.

.. toctree::
   :maxdepth: 1

   reference/protocol
   reference/models
   reference/lifecycle
   reference/pyproject
   reference/archive
   reference/settings
   reference/loader
   reference/installer
   reference/toolkit
   reference/registry
   reference/resources
   reference/testing
   reference/docs
   reference/admin
   reference/exceptions
