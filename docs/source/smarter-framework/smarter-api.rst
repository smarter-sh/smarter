Smarter API
================================

The Smarter API provides support for :doc:`AI text prompts <../smarter-resources/smarter-prompt>`,
the :doc:`command-line interface (CLI) <../smarter-platform/cli>`, as well as
limited support for anciallary UI features. The API is built on :doc:`Django REST Framework <developer-reference/lib/drf>` and
includes a rich set of enterprise features for enhanced security, audit capability,
and performance optimization.

Its official clients are the :doc:`Smarter CLI <smarter-cli>`, for people at a terminal, and the
:doc:`Python <smarter-python>`, :doc:`Node.js <smarter-nodejs>` and :doc:`Go <smarter-golang>`
SDKs, for software that integrates with your platform.

The whole API is described by a typed OpenAPI 3.1 document, the
:doc:`Smarter OpenAPI Contract <smarter-openapi>`, which every platform serves at
``/docs/openapi.json``, and from which clients in any language can be generated. See
:doc:`Smarter APIs, SDKs and Integrations <apis-and-sdks>` for the design that the API and its clients share.

The Smarter Framework supports multiple hosting naming schemes for the Smarter API. For example:


.. list-table:: Smarter API Hosting Schemes
   :header-rows: 1

   * - Hosting Type
     - Example
   * - Default Hosting
     - ``api.example.com``
   * - Session-Based Hosting
     - ``example.com/v1/api/``
   * - Named LLMClients
     - ``stackademy.1234-5678-9012.example.com``
   * - Custom Domains
     - ``chat.yourdomain.com``

See :doc:`developer-reference/lib/django/hosts` for more details.

.. automodule:: smarter.apps.api.v1.urls
   :members:
   :undoc-members:
   :show-inheritance:

.. literalinclude:: ../../../smarter/smarter/apps/api/v1/urls.py
   :language: python
   :linenos:
   :lines: 28-


.. toctree::
  :maxdepth: 1
  :caption: Technical Reference

  smarter-api/documentation
  smarter-api/cli
  smarter-api/api-contract
  smarter-api/chat
  smarter-api/authentication
  smarter-api/error-handling
  smarter-api/logging
  smarter-api/rate-limiting
  smarter-api/smarter-journal
  smarter-api/code
