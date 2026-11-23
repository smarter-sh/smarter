Errors and Reliability
======================

Exceptions
----------

Every exception that the SDK raises is a ``SmarterError``, so one ``except`` clause catches them
all. The SDK follows the platform's own rule that exceptions subclass one hierarchy
(:doc:`Smarter ADR-012 </adr/012-error-handling>`).

.. code-block:: text

   SmarterError
   ├── SmarterConfigurationError        the client has no api key or base url
   ├── SmarterValueError                an argument is invalid, before any request is sent
   ├── ResourceNotFoundError            a resource was not found, by the API or by find()
   ├── SmarterPromptError               a streamed prompt failed
   └── APIError
       ├── APIConnectionError           the request got no response
       │   └── APITimeoutError
       ├── APIResponseValidationError   the response doesn't match the SDK's model of it
       └── APIStatusError               the API returned a 4xx or 5xx status
           ├── BadRequestError          400
           ├── AuthenticationError      401
           ├── PaymentRequiredError     402, a budget refused the charge
           ├── PermissionDeniedError    403
           ├── NotFoundError            404, also a ResourceNotFoundError
           ├── ConflictError            409
           ├── UnprocessableEntityError 422
           ├── RateLimitError           429
           └── InternalServerError      5xx

An ``APIStatusError`` carries the response's ``status_code``, a readable ``message``, the parsed
``body``, and, when the platform sent a journaled error, its ``error``, whose ``errorClass`` (also
``error_class``) is the name of the platform's exception, e.g. ``SAMBrokerErrorNotFound``.

.. code-block:: python

   from smarter import NotFoundError, SmarterError

   try:
       client.manifests.describe("LLMClient", "no_such_client")
   except NotFoundError as e:
       print(e.status_code, e.message, e.error_class)
   except SmarterError as e:
       print("something else went wrong:", e)

A ``PaymentRequiredError`` means that one of the platform's budgets refused the charge: it has
locked the account, the user's profile, or the resource, e.g. a Vectorsearch or a Proxy, until it
allows spending again. Retrying won't help before then, so the SDK never retries a 402.

An ``APIResponseValidationError`` usually means that the SDK and the platform are of incompatible
versions. Compare ``client.version().api.version`` with the SDK's ``smarter.__version__``.

Retries and timeouts
--------------------

A request that failed for a transient reason is retried, by default twice, with exponential backoff
and jitter, honoring the response's ``Retry-After``. Transient means: no response, a timeout, or a
408, 429, 502 or 504 status. A 503 is retried only when it didn't come from the platform itself,
e.g. from a load balancer, because the platform answers 503 for a resource that isn't ready, which a
retry won't change. Any other 4xx, e.g. a 402, is raised at once.

.. code-block:: python

   client = Smarter(max_retries=0, timeout=120)

Retrying a prompt can bill a prompt twice, if the first attempt reached the LLM. Set
``max_retries=0`` where that matters more than resilience. A request that must not be sent twice
is never retried, whatever the client's setting: ``accounts.data_exports.start()``, whose 429 is a
refusal that a retry would not change. ``client.http.request()`` takes ``max_retries`` for one
request, too.

Logging
-------

The SDK logs to the ``smarter`` logger hierarchy, and, as a library should, adds no handlers unless
you ask it to. Set ``SMARTER_LOG=info`` to log each request's method, url, status and duration to
stderr, or ``SMARTER_LOG=debug`` to log the bodies too. Or configure the logger as any other:

.. code-block:: python

   import logging

   logging.getLogger("smarter.client").setLevel(logging.DEBUG)

API keys are never logged: they are masked to their last four characters.
