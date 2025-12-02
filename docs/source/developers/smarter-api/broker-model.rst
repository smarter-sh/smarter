CLI Broker Model
================================

The Smarter Broker Model for the command-line interface (CLI) establishes an abstract set of pattnerns
for implementing a static set of commands operated on Smarter yaml manifest files. These are operations
that are intended to be initiated by the Smarter CLI tool. See `github.com/smarter-sh/smarter-cli <https://github.com/smarter-sh/smarter-cli>`__.

See :doc:`base/cli-base` for details on the base CLI view CliBaseApiView.

.. autoclass:: smarter.apps.api.v1.cli.brokers.Brokers
   :members:
   :undoc-members:
   :show-inheritance:

AI Resources that implement the Broker Model will subclass the AbstractBroker class.

.. autoclass:: smarter.lib.manifest.broker.AbstractBroker
   :members:
   :undoc-members:
   :show-inheritance:
