API Documentation
=============================

Every Smarter platform documents its api in the web console's sidebar:

- **OpenAPI Contract** (``/docs/openapi/``) renders the typed OpenAPI 3.1 document of the Smarter api,
  which is also served as ``/docs/openapi.json``, to generate clients and SDKs from. See
  :doc:`api-contract`.
- **Swagger** (``/docs/swagger/``) and **Redoc** (``/docs/redoc/``) are generated from the
  platform's views, in OpenAPI 2, and cover every endpoint, but without typed request and response
  bodies.

The Smarter Project's own `Swagger <https://docs.smarter.sh/swagger/>`_ and
`Redoc <https://docs.smarter.sh/redoc/>`_ pages are public.
