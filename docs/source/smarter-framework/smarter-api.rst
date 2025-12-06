Smarter Api
================================

The Smarter API provides support for AI text completion, the command-line interface (CLI), as well as
limited support for anciallary UI features. The API is built on Django REST Framework and
includes a rich set of enterprise features for enhanced security, audit capability,
and performance optimization.

The Smarter Framework supports multiple hosting naming schemes for the Smarter API. For example:

.. list-table:: Smarter API Hosting Schemes
   :header-rows: 1

   * - Hosting Type
     - Example
   * - Default Hosting
     - ``api.example.com``
   * - Session-Based Hosting
     - ``example.com/v1/api/``
   * - Named Chatbots
     - ``stackademy.1234-5678-9012.example.com``
   * - Custom Domains
     - ``chat.yourdomain.com``

See :doc:`django/hosts` for more details.

.. automodule:: smarter.apps.api.v1.urls
   :members:
   :undoc-members:
   :show-inheritance:

.. toctree::
   :maxdepth: 1

   smarter-api/authentication
   smarter-api/base-class
   smarter-api/cli
   smarter-api/error-handling
   smarter-api/logging
   smarter-api/rate-limiting
   smarter-api/smarter-journal

Smarter AI Resource Enumerations
---------------------------------

The Smarter API is designed to provide a robust and flexible interface for interacting with Smarter AI resources,
which include the following. See :doc:`smarter-journal/enumerations`
