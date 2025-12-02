Smarter Api
================================

The Smarter API provides support for AI text completion, the command-line interface (CLI), as well as
limited support for anciallary UI features. The API is built on Django REST Framework and
includes a rich set of enterprise features for enhanced security, audit capability,
and performance optimization.

.. automodule:: smarter.apps.api.v1.urls
   :members:
   :undoc-members:
   :show-inheritance:

.. toctree::
   :maxdepth: 1

   smarter-api/authentication
   smarter-api/base-class
   smarter-api/broker-model
   smarter-api/cli
   smarter-api/error-handling
   smarter-api/logging
   smarter-api/rate-limiting
   smarter-api/smarter-journal

Smarter AI Resource Enumerations
---------------------------------

The Smarter API is designed to provide a robust and flexible interface for interacting with Smarter AI resources,
which include the following.

.. autoclass:: smarter.lib.journal.enum.SmarterJournalThings
   :members:
   :undoc-members:
   :show-inheritance:
