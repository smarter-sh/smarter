Errors and Reliability
======================

Errors
------

Every error that the SDK throws is a ``SmarterError``, so one ``instanceof`` test catches them all.
The classes, their names and their hierarchy are the :doc:`Python SDK's <../smarter-python/errors>`,
which follows the platform's own rule (:doc:`ADR-012 <../../adr/012-error-handling>`).

.. code-block:: text

   SmarterError
   ├── SmarterConfigurationError        the client has no api key or base url
   ├── SmarterValueError                an argument is invalid, before any request is sent
   ├── ResourceNotFoundError            a resource was not found, by the API or by find()
   ├── SmarterPromptError               a streamed prompt failed
   └── APIError
       ├── APIConnectionError           the request got no response
       │   └── APITimeoutError
       ├── APIResponseValidationError   the response doesn't match the SDK's schema of it
       └── APIStatusError               the API returned a 4xx or 5xx status
           ├── BadRequestError          400
           ├── AuthenticationError      401
           ├── PermissionDeniedError    403
           ├── NotFoundError            404, also an instanceof ResourceNotFoundError
           ├── ConflictError            409
           ├── UnprocessableEntityError 422
           ├── RateLimitError           429
           └── InternalServerError      5xx

An ``APIStatusError`` carries the response's ``statusCode``, a readable ``message``, the parsed
``body``, the ``headers``, and, when the platform sent a journaled error, its ``error``, whose
``errorClass`` (also on the error itself) is the name of the platform's exception, e.g.
``SAMBrokerErrorNotFound``.

.. code-block:: typescript

   import { NotFoundError, SmarterError } from "smarter-api";

   try {
     await client.manifests.describe("LLMClient", "no_such_client");
   } catch (err) {
     if (err instanceof NotFoundError) console.log(err.statusCode, err.message, err.errorClass);
     else if (err instanceof SmarterError) console.log("something else went wrong:", err);
     else throw err;
   }

Every method that sends a request is ``async``, so its errors are rejections, also those of its
arguments, e.g. an invalid id. An ``APIResponseValidationError`` usually means that the SDK and the
platform are of incompatible versions. Compare ``(await client.version()).api.version`` with the
SDK's ``VERSION``.

Retries and timeouts
--------------------

A request that failed for a transient reason is retried, by default twice, with exponential backoff
and jitter, honoring the response's ``Retry-After``. Transient means: no response, a timeout, or a
408, 429, 502 or 504 status. A 503 is retried only when it didn't come from the platform itself,
e.g. from a load balancer, because the platform answers 503 for a resource that isn't ready, which a
retry won't change.

.. code-block:: typescript

   const client = new Smarter({ maxRetries: 0, timeout: 120 });
   await client.llmClients.prompt(llmclient.id, "Hello", { timeout: 300 }); // for this request only

The timeout is in seconds. For a stream, it applies to each event, so a long prompt that reports
its progress doesn't time out.

Retrying a prompt can bill a prompt twice, if the first attempt reached the LLM. Set
``maxRetries: 0`` where that matters more than resilience.

Cancellation
------------

Every method takes an ``AbortSignal``. Aborting it cancels the request, and the promise rejects with
the signal's reason. A stream is cancelled when you ``break`` out of its loop.

.. code-block:: typescript

   const controller = new AbortController();
   setTimeout(() => controller.abort(), 5000);
   await client.llmClients.prompt(llmclient.id, "Hello", { signal: controller.signal });

Logging
-------

As a library should, the SDK logs nothing unless you ask it to. Pass a ``logger`` (``console``, or a
pino, winston or bunyan logger), and set ``SMARTER_LOG=info`` (or the ``logLevel`` option) to log each
request's method, url, status and duration, or ``debug`` to log the bodies too. Without a ``logger``,
a level logs to ``console``.

.. code-block:: typescript

   import pino from "pino";

   const client = new Smarter({ logger: pino(), logLevel: "info" });

API keys are never logged: they are masked to their last four characters, also when you
``console.log()`` or ``JSON.stringify()`` the client.
