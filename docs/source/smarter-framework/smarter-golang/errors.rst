Errors and Reliability
======================

Errors
------

Every error that the SDK returns matches ``smarter.ErrSmarter`` with ``errors.Is``. The
:doc:`Python SDK's <../smarter-python/errors>` exception hierarchy, which follows the platform's own
rule (:doc:`ADR-012 <../../adr/012-error-handling>`), becomes Go's sentinel errors and error types:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Check
     - Means
   * - ``errors.Is(err, smarter.ErrSmarter)``
     - Any error of the SDK.
   * - ``errors.As(err, &configurationError)``
     - ``*smarter.ConfigurationError``: the client has no api key, or a value is invalid.
   * - ``errors.As(err, &valueError)``
     - ``*smarter.ValueError``: an argument is invalid, before any request is sent.
   * - ``errors.Is(err, smarter.ErrResourceNotFound)``
     - A resource was not found, by the API (a 404) or by ``Find``.
   * - ``errors.As(err, &connectionError)``
     - ``*smarter.APIConnectionError``: the request got no response. ``Timeout()`` reports a timeout.
   * - ``errors.As(err, &validationError)``
     - ``*smarter.APIResponseValidationError``: the response doesn't decode into the SDK's struct.
   * - ``errors.As(err, &statusError)``
     - ``*smarter.APIStatusError``: the API returned a 4xx or 5xx status.
   * - ``errors.Is(err, smarter.ErrBadRequest)``, ``ErrAuthentication``, ``ErrPermissionDenied``,
       ``ErrNotFound``, ``ErrConflict``, ``ErrUnprocessableEntity``, ``ErrRateLimit``,
       ``ErrInternalServer``
     - The status: 400, 401, 403, 404, 409, 422, 429, and 5xx.
   * - ``errors.As(err, &promptError)``
     - ``*smarter.PromptError``: a streamed prompt failed.

An ``*APIStatusError`` carries the response's ``StatusCode``, a readable ``Message``, the ``Body``,
the ``Header``, and, when the platform sent a journaled error, its ``JournalError``, whose
``ErrorClass()`` is the name of the platform's exception, e.g. ``SAMBrokerErrorNotFound``. The checks
keep working through your own ``fmt.Errorf("...: %w", err)``.

.. code-block:: go

   _, err := client.Manifests.Describe(ctx, "LLMClient", "no_such_client")
   var status *smarter.APIStatusError
   switch {
   case errors.Is(err, smarter.ErrNotFound) && errors.As(err, &status):
       fmt.Println(status.StatusCode, status.Message, status.ErrorClass())
   case errors.Is(err, smarter.ErrSmarter):
       fmt.Println("something else went wrong:", err)
   }

An ``*APIResponseValidationError`` usually means that the SDK and the platform are of incompatible
versions. Compare the platform's ``client.Version(ctx)`` with the SDK's ``smarter.Version``.

Retries and timeouts
--------------------

A request that failed for a transient reason is retried, by default twice, with exponential backoff
and jitter, honoring the response's ``Retry-After``. Transient means: no response, a timeout, or a
408, 429, 502 or 504 status. A 503 is retried only when it didn't come from the platform itself,
e.g. from a load balancer, because the platform answers 503 for a resource that isn't ready, which a
retry won't change.

.. code-block:: go

   client, err := smarter.NewClient(smarter.WithMaxRetries(0), smarter.WithTimeout(2*time.Minute))

The timeout applies to each attempt. For a stream, it applies to each event, so a long prompt that
reports its progress doesn't time out. Retrying a prompt can bill a prompt twice, if the first
attempt reached the LLM. Set ``WithMaxRetries(0)`` where that matters more than resilience.

Cancellation
------------

Every method takes a ``context.Context``. Cancelling it, or its deadline, ends the request at once,
also while the SDK waits to retry, and the error wraps the context's error:

.. code-block:: go

   ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
   defer cancel()
   _, err := client.LLMClients.Prompt(ctx, llmclient.Ref(), smarter.Text("Hello"), nil)
   if errors.Is(err, context.DeadlineExceeded) {
       fmt.Println("gave up")
   }

Logging
-------

As a library should, the SDK logs nothing unless you ask it to. Give it your ``*slog.Logger`` with
``smarter.WithLogger``: it logs each request's method, url, status and duration at the info level,
and the bodies at the debug level, with the attribute ``component=smarter``. Without a logger,
``SMARTER_LOG=info`` or ``SMARTER_LOG=debug`` logs to stderr.

.. code-block:: go

   client, err := smarter.NewClient(smarter.WithLogger(slog.Default()))

API keys are never logged: they are masked to their last four characters, also when you print or
``slog`` the client.
