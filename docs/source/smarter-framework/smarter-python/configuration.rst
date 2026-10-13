Configuration
=============

A client needs a Smarter API key and the url of your Smarter platform. Every argument of
``Smarter(...)`` is optional, because each value is looked up in this order:

1. the arguments of ``Smarter(...)``,
2. environment variables,
3. the :doc:`Smarter CLI's <../smarter-cli>` configuration file, ``~/.smarter/config.yaml``,
4. the defaults: the ``prod`` environment of ``platform.smarter.sh``.

.. code-block:: python

   from smarter import Smarter

   client = Smarter(
       api_key="your 64-character Smarter api key",
       base_url="https://platform.example.com",
       timeout=60,
       max_retries=2,
   )

API keys
--------

An API key belongs to a user of an account, and the SDK can do whatever that user can do. Create
one in the web console, or with a ``SmarterAuthToken`` manifest. See
:doc:`Authentication <../smarter-api/authentication>`. Keep it out of your source code: use an
environment variable or a secret manager.

Environment variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Meaning
   * - ``SMARTER_API_KEY``
     - The API key.
   * - ``SMARTER_BASE_URL``
     - Your platform's url, e.g. ``https://platform.example.com`` or ``http://localhost:9357``.
       The API's path, ``/api/v1/``, is added for you.
   * - ``SMARTER_ENVIRONMENT``
     - ``local``, ``alpha``, ``beta``, ``next`` or ``prod``: which environment of the CLI's
       configuration file to use, and how to derive the url when there is no base url.
   * - ``SMARTER_ROOT_DOMAIN``
     - The platform's root domain, e.g. ``platform.example.com``, for deriving the url.
   * - ``SMARTER_TIMEOUT``
     - Seconds to wait for a response. The default is 60, because a prompt that calls several
       tools can take tens of seconds.
   * - ``SMARTER_MAX_RETRIES``
     - How many times to retry a request that failed for a transient reason. The default is 2.
   * - ``SMARTER_LOG``
     - ``info`` logs each request to stderr, and ``debug`` its body too. API keys are never logged.
   * - ``SMARTER_CONFIG_FILE``
     - Another path for the CLI's configuration file.

Without a base url, the url is derived from the environment, exactly as the CLI derives it:
``local`` is ``http://localhost:9357``, ``alpha``, ``beta`` and ``next`` are
``https://<environment>.<root domain>``, and ``prod`` is ``https://<root domain>``.

Sharing the CLI's configuration
-------------------------------

``smarter configure`` writes the CLI's configuration file, with an API key per environment:

.. code-block:: yaml

   config:
     environment: local
     root_domain: platform.example.com
   local:
     api_key: <your local api key>
   prod:
     api_key: <your production api key>

The SDK reads it too, so ``Smarter()`` connects to the CLI's current environment, with that
environment's key, and ``Smarter(environment="prod")`` to another one.

Your own HTTP client
--------------------

Pass an ``httpx.Client`` to send requests through a corporate proxy, with custom TLS settings, or
through a test transport. The SDK never closes a client that you passed in.

.. code-block:: python

   import httpx
   from smarter import Smarter

   client = Smarter(http_client=httpx.Client(proxy="http://proxy.example.com:3128", verify="ca.pem"))

Use a client as a context manager, or call ``close()``, to close its connections:

.. code-block:: python

   with Smarter() as client:
       print(client.whoami().account.account_number)
