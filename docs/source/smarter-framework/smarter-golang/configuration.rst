Configuration
=============

A client needs a Smarter API key and the url of your Smarter platform. Every option of
``smarter.NewClient(...)`` is optional, because each value is looked up in this order:

1. the options of ``smarter.NewClient(...)``,
2. environment variables,
3. the :doc:`Smarter CLI's <../smarter-cli>` configuration file, ``~/.smarter/config.yaml``,
4. the defaults: the ``prod`` environment of ``platform.smarter.sh``.

This is the lookup of every Smarter SDK and of the CLI itself, so the same environment configures
them all.

.. code-block:: go

   client, err := smarter.NewClient(
       smarter.WithAPIKey("your 64-character Smarter api key"),
       smarter.WithBaseURL("https://platform.example.com"),
       smarter.WithTimeout(60*time.Second),
       smarter.WithMaxRetries(2),
   )

``NewClient`` returns a ``*smarter.ConfigurationError`` when there is no API key, or a value is
invalid. A client is safe for concurrent use: create one, and share it.

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
     - Seconds to wait for a response, as in every Smarter SDK. The default is 60, because a prompt
       that calls several tools can take tens of seconds.
   * - ``SMARTER_MAX_RETRIES``
     - How many times to retry a request that failed for a transient reason. The default is 2.
   * - ``SMARTER_LOG``
     - ``info`` logs each request to stderr, and ``debug`` its body too. API keys are never logged.
       See :doc:`Errors and Reliability <errors>`.
   * - ``SMARTER_CONFIG_FILE``
     - Another path for the CLI's configuration file.

Without a base url, the url is derived from the environment, exactly as the CLI derives it:
``local`` is ``http://localhost:9357``, ``alpha``, ``beta`` and ``next`` are
``https://<environment>.<root domain>``, and ``prod`` is ``https://<root domain>``.
``smarter.EnvironmentURL`` derives it for you.

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

The SDK reads it too, so ``smarter.NewClient()`` connects to the CLI's current environment, with
that environment's key, and ``smarter.NewClient(smarter.WithEnvironment(smarter.EnvironmentProd))``
to another one.

Your own HTTP client
--------------------

Pass an ``*http.Client`` to send requests through a corporate proxy, with custom TLS settings, or
through a test ``RoundTripper``. Leave its ``Timeout`` at 0: the SDK applies its own timeout to each
attempt.

.. code-block:: go

   proxy, _ := url.Parse("http://proxy.example.com:3128")
   client, err := smarter.NewClient(smarter.WithHTTPClient(&http.Client{
       Transport: &http.Transport{Proxy: http.ProxyURL(proxy)},
   }))

``smarter.WithHeader`` adds a header to every request, and ``smarter.WithLookupEnv`` replaces the
function that reads environment variables, e.g. in a test.
