Smarter Proxy
=====================

Overview
--------

A Smarter Proxy gives passthrough access to a third-party LLM provider's API, such as
OpenAI's, Anthropic's or Google Gemini's, with an API key that Smarter keeps as a
:doc:`Secret <smarter-secret>`.

Callers use the provider's own SDK, unchanged. They set the SDK's base URL to the Proxy's URL,
and use a Smarter API key in place of the provider's. Smarter forwards each request to the
provider as it is, adds the provider's API key, and returns the provider's response as it is,
including streams. The only difference from calling the provider directly is the API key: the
provider's key never leaves Smarter, so it is never distributed to developers, applications or
CI pipelines, and it can be rotated in one place.

Because every request passes through Smarter, Proxies also give you:

- **Smarter API keys** in place of provider keys. They can be revoked per user.
- **Path restrictions**, e.g. to allow chat completions and embeddings, but not the provider
  account's files, fine-tuning jobs or settings.
- **Budget controls.** A budget's resource lock refuses requests.
- **Usage accounting.** The tokens of each request, as the provider reports them, are charged
  to the Proxy, the caller, and the caller's account.

.. note::

   The Smarter Proxy is included in v0.16.0 and later. It is enabled by default. Set the
   environment variable ``SMARTER_ENABLE_PROXY=false`` to disable it.

.. seealso::

   - :doc:`Smarter Provider <smarter-provider>`: a Proxy forwards to a Provider's API.
   - :doc:`Smarter Secret <smarter-secret>`: a Proxy's provider API key is a Secret.
   - :doc:`Smarter API keys <smarter-authtoken>`: callers authenticate with one.

How It Works
------------

.. code-block:: text

   your app (provider SDK)                Smarter                          LLM provider
   ------------------------  Smarter API key  -----------------  provider API key  ----------------
   POST .../api/v1/proxy/openai/chat/completions  ->  POST https://api.openai.com/v1/chat/completions

A Proxy's URL is ``https://<your Smarter platform>/api/v1/proxy/<proxy name>/``. Everything after
it is a path relative to the Proxy's base URL, e.g. ``chat/completions``. For each request, Smarter:

1. Authenticates the caller's Smarter API key, and finds the Proxy by name: the caller's own
   Proxy, else their account's, else the built-in one.
2. Refuses the request if the Proxy is inactive, the path is not one of its ``allowedPaths``, or
   a budget forbids it.
3. Removes the caller's credentials, cookies, and connection headers, adds the Proxy's
   ``headers``, and adds the provider's API key from the Proxy's Secret.
4. Sends the request to ``<baseUrl><path>``, with the query string and body as they are, and
   returns the provider's status, headers and body. Server-sent event streams are streamed.
5. Reads the token usage from the response, or from the stream as it ends, and charges it.

Errors of the provider, e.g. a 429 rate limit, are returned to the caller as they are.

Quick Start
-----------

Smarter includes a built-in Proxy for each of its built-in Providers that has an API key. Every
account may use them. See `Built-in Proxies`_. To list the Proxies that you may use:

.. code-block:: console

   smarter get proxies

   curl -H "Authorization: Bearer $SMARTER_API_KEY" https://platform.smarter.sh/api/v1/proxy/

Then point the provider's SDK at a Proxy, with your Smarter API key.

**OpenAI**, and OpenAI-compatible APIs:

.. code-block:: python

   from openai import OpenAI

   client = OpenAI(
       base_url="https://platform.smarter.sh/api/v1/proxy/openai/",
       api_key=SMARTER_API_KEY,
   )
   response = client.chat.completions.create(
       model="gpt-6-luna",
       messages=[{"role": "user", "content": "Hello!"}],
   )

**Anthropic**. The SDK adds ``/v1/`` to its paths, so the ``anthropic`` Proxy's base URL does not
include it:

.. code-block:: python

   from anthropic import Anthropic

   client = Anthropic(
       base_url="https://platform.smarter.sh/api/v1/proxy/anthropic/",
       api_key=SMARTER_API_KEY,
   )
   message = client.messages.create(
       model="claude-sonnet-4-6",
       max_tokens=1024,
       messages=[{"role": "user", "content": "Hello!"}],
   )

**Google Gemini**:

.. code-block:: python

   from google import genai

   client = genai.Client(
       api_key=SMARTER_API_KEY,
       http_options={"base_url": "https://platform.smarter.sh/api/v1/proxy/googleai/"},
   )
   response = client.models.generate_content(model="gemini-2.5-flash", contents="Hello!")

**curl**:

.. code-block:: console

   curl https://platform.smarter.sh/api/v1/proxy/openai/chat/completions \
     -H "Authorization: Bearer $SMARTER_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-6-luna", "messages": [{"role": "user", "content": "Hello!"}]}'

Creating a Proxy
----------------

Create your own Proxy to use your own provider API key, another base URL, or other path
restrictions. First, create a Secret with the provider's API key, then apply a Proxy manifest
that names it:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Proxy
   metadata:
     name: my_anthropic
     description: Anthropic's Messages API, with our team's API key.
     version: 1.0.0
   spec:
     provider: anthropic                # the name of a Provider
     apiKey: my_anthropic_api_key       # the name of a Secret of your account
     baseUrl: https://api.anthropic.com/
     auth:
       header: x-api-key
       scheme: ""
     headers:
       anthropic-version: "2023-06-01"
     allowedPaths:
       - v1/messages
       - v1/messages/count_tokens
       - v1/models
       - v1/models/*
     timeout: 300
     isActive: true

.. code-block:: console

   smarter apply -f my-anthropic-proxy.yaml
   smarter describe proxy my_anthropic

A Proxy is shared, read-only, with every user of its owner's account: each of them may call
it, and only its owner may change or delete it.

``smarter describe`` reports the Proxy's URL, the base URL that it forwards to, and the name of
the Secret whose API key it sends. ``smarter manifest proxy`` prints an example manifest. In the
web console, Proxies are listed under **Proxies**, where they can be cloned, renamed and deleted,
and their URLs copied.

Manifest Reference
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Default
     - Description
   * - ``spec.provider``
     - required
     - The name of a :doc:`Provider <smarter-provider>` that you may use, e.g. a built-in one.
   * - ``spec.apiKey``
     - the Provider's
     - The name of the Secret that contains the provider's API key. It must belong to your
       account. If it is not set, the Provider's API key is used, if it belongs to your account.
   * - ``spec.baseUrl``
     - the Provider's
     - The base URL of the provider's API, to which paths are appended, e.g.
       ``https://api.openai.com/v1/``.
   * - ``spec.auth.header``
     - ``Authorization``
     - The header in which the provider expects its API key: ``Authorization`` for OpenAI and
       OpenAI-compatible APIs, ``x-api-key`` for Anthropic, ``x-goog-api-key`` for Google Gemini,
       ``api-key`` for Azure OpenAI.
   * - ``spec.auth.scheme``
     - ``Bearer``
     - The prefix of the API key in the header. Empty for none, e.g. for ``x-api-key``.
   * - ``spec.headers``
     - none
     - Headers added to every request, e.g. ``anthropic-version``. They replace the caller's
       headers of the same name. Credential, cookie, host and connection headers are not allowed.
   * - ``spec.allowedPaths``
     - all paths
     - Glob patterns of the paths, relative to the base URL, that callers may use, e.g.
       ``chat/completions`` or ``models/*``. ``*`` also matches ``/`` and ``:``, so ``models/*``
       matches ``models/gemini-2.5-flash:generateContent``. Paths that would leave the base URL,
       e.g. with ``..``, are always refused.
   * - ``spec.timeout``
     - ``120``
     - The most seconds, up to 600, to wait for the provider's response.
   * - ``spec.isActive``
     - ``true``
     - An inactive Proxy refuses every request.

Unknown fields are refused, to catch typos.

Authentication
--------------

Callers authenticate with a :doc:`Smarter API key <smarter-authtoken>`, in any of the headers
that LLM SDKs send their API key in, so that each SDK works unchanged:

- ``Authorization: Bearer <key>``: OpenAI, and OpenAI-compatible SDKs. ``Authorization: Token <key>``,
  as for the rest of the Smarter API, also works.
- ``x-api-key: <key>``: Anthropic.
- ``x-goog-api-key: <key>``: Google Gemini.
- ``api-key: <key>``: Azure OpenAI.

None of them is forwarded to the provider. The web console's session does not authenticate the
passthrough, so that other web sites cannot use it on a signed-in user's behalf.

Errors
------

Errors of Smarter's own are JSON, in the shape that the OpenAI and Anthropic SDKs report:
``{"error": {"message": "...", "type": "smarter_proxy_error", "code": "..."}}``.

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Status
     - Code
     - Meaning
   * - 401
     -
     - The Smarter API key is missing, invalid or inactive.
   * - 402
     - ``budget_exceeded``
     - A budget's resource lock forbids charges to the Proxy, the caller, or their account.
   * - 403
     - ``proxy_inactive``
     - The Proxy's ``isActive`` is false.
   * - 403
     - ``path_not_allowed``
     - The path is not one of the Proxy's ``allowedPaths``, or would leave its base URL.
   * - 404
     - ``proxy_not_found``
     - You may use no Proxy of that name.
   * - 502
     - ``upstream_unreachable``
     - The provider cannot be reached.
   * - 503
     - ``proxy_misconfigured``
     - The Proxy has no base URL or API key, its API key Secret is expired or belongs to another
       account, or its base URL is not on the public internet.
   * - 504
     - ``upstream_timeout``
     - The provider did not respond within the Proxy's ``timeout``.

Each response that Smarter forwards has an ``X-Smarter-Proxy`` header, with the Proxy's name.

Security
--------

- **Provider API keys never leave Smarter.** They are read from their Secret for each request,
  and are never logged, returned, or shown in manifests, where Secrets are named, not revealed.
- **A Proxy may only send its own account's Secrets.** Otherwise anyone could write a Proxy
  that sends another account's API key, e.g. the platform's, to a base URL of their choosing.
  This is checked when the manifest is applied, and again for each request. So a clone of a
  built-in Proxy needs a ``spec.apiKey`` of your own.
- **Proxies cannot reach Smarter's internal network.** A base URL whose host is a private,
  loopback or link-local address, e.g. a cloud metadata service, is refused, unless a superuser
  owns the Proxy, e.g. to forward to an LLM inside the cluster.
- **Redirects are not followed**, so the provider's API key is only ever sent to the base URL.
- **The caller's credentials, cookies and address** (``X-Forwarded-For`` and the like) are not
  forwarded, and the provider's cookies are not returned.
- **The built-in Proxies allow only inference endpoints**, so that the platform's provider
  accounts' files, fine-tuning jobs, batches and settings cannot be reached through them.

Usage and Budgets
-----------------

Smarter reads the token usage that the provider reports in each response: ``usage`` (OpenAI,
Anthropic, Cohere v2), ``usageMetadata`` (Google Gemini), or ``meta.billed_units`` (Cohere v1).
For a server-sent event stream, it reads the usage from the stream's events as they pass
through, e.g. OpenAI's final chunk with ``stream_options: {"include_usage": true}``, or
Anthropic's ``message_start`` and ``message_delta`` events. The usage is charged, as a
completion charge, to the Proxy, the caller, and the caller's account.

Before forwarding a request, Smarter checks that no budget's resource lock forbids charges to
any of them, and otherwise refuses it with 402.

Built-in Proxies
----------------

``manage.py initialize_platform`` applies a built-in Proxy for each built-in Provider whose API
key is configured, e.g. with the ``OPENAI_API_KEY`` environment variable. The Smarter admin owns
them, so every account may use them. A Proxy whose Provider or API key does not exist is skipped.
To apply them again, e.g. after adding an API key:

.. code-block:: console

   python manage.py initialize_providers
   python manage.py add_builtin_proxies

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Proxy
     - SDK
     - Allowed paths
   * - ``openai``
     - OpenAI
     - chat/completions, completions, responses, embeddings, moderations, models
   * - ``anthropic``
     - Anthropic
     - v1/messages, v1/messages/count_tokens, v1/models
   * - ``googleai``
     - Google Gen AI
     - v1beta/models/\*, v1/models/\*, e.g. ``generateContent`` and ``embedContent``
   * - ``googleai_openai``
     - OpenAI
     - chat/completions, embeddings, models: Gemini's OpenAI-compatible API
   * - ``mistral``
     - Mistral, or OpenAI with ``.../v1/``
     - v1/chat/completions, v1/fim/completions, v1/embeddings, v1/moderations, v1/models
   * - ``cohere``
     - Cohere
     - v2/chat, v2/embed, v2/rerank, and their v1 equivalents, v1/models
   * - ``fireworks``
     - OpenAI
     - chat/completions, completions, embeddings, models
   * - ``togetherai``
     - Together, or OpenAI
     - chat/completions, completions, embeddings, models
   * - ``metaai``
     - Llama API, or OpenAI with ``.../compat/v1/``
     - v1/chat/completions, v1/moderations, v1/models, compat/v1/chat/completions

Their manifests are in ``smarter/apps/proxy/data/proxy/``, and are shown in
:doc:`proxy/manifest/example-manifests`.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   proxy/api
   proxy/authentication
   proxy/caching
   proxy/const
   proxy/exceptions
   proxy/management
   proxy/manifest
   proxy/models
   proxy/serializers
   proxy/services
   proxy/signals
   proxy/views
