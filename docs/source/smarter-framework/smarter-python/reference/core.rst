..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

Configuration, Transport and Errors
===================================

``smarter.core.conf``
---------------------

.. py:module:: smarter.core.conf

The configuration of the Smarter SDK.

A client needs an api key and the base url of a Smarter platform. Each is taken from the first of
these that sets it:

1. the arguments of :class:`smarter.Smarter`,
2. environment variables: ``SMARTER_API_KEY``, ``SMARTER_BASE_URL``, ``SMARTER_ENVIRONMENT``,
   ``SMARTER_ROOT_DOMAIN``, ``SMARTER_TIMEOUT``, ``SMARTER_MAX_RETRIES`` and ``SMARTER_LOG``
   (:class:`SmarterSettings`),
3. the ``smarter`` cli's configuration file, ``~/.smarter/config.yaml`` (``SMARTER_CONFIG_FILE``),
   so that a developer who has run ``smarter configure`` needs no other setup,
4. the defaults: the ``prod`` environment of ``platform.smarter.sh``.

Without an explicit base url, the url is derived from the environment as the cli derives it:
``local`` is ``http://localhost:9357``, ``alpha``, ``beta`` and ``next`` are
``https://<environment>.<root domain>``, and ``prod`` is ``https://<root domain>``.

This follows the Smarter platform's settings design (ADR-007): one validated Pydantic settings
model is the only place that reads the environment.

.. py:data:: SmarterEnvironment

   The environments of the smarter cli's configuration file.

.. py:data:: LOCAL_URL

   The url of the Smarter platform's local development server.

.. py:data:: API_PATH

   The path of the Smarter api, which every request url is relative to.

.. py:data:: DEFAULT_TIMEOUT

   Seconds.

   Prompts that call several tools can take tens of seconds.

.. py:class:: SmarterSettings

   Bases: :class:`pydantic_settings.main.BaseSettings`

   The SDK's settings, from ``SMARTER_*`` environment variables.

   .. py:attribute:: api_key
      :type: Optional

      A Smarter api key: 64 characters.


   .. py:attribute:: base_url
      :type: Optional

      e.g. https://platform.example.com or http://localhost:9357.


   .. py:attribute:: environment
      :type: Optional


   .. py:attribute:: root_domain
      :type: Optional

      The platform's root domain, e.g. platform.smarter.sh.


   .. py:attribute:: timeout
      :type: float


   .. py:attribute:: max_retries
      :type: int


   .. py:attribute:: config_file
      :type: Path


   .. py:attribute:: log
      :type: Optional

      Log the SDK's requests to stderr.



.. py:class:: CliConfig

   Bases: :class:`pydantic.main.BaseModel`

   The parts of the smarter cli's ``~/.smarter/config.yaml`` that the SDK reads.

   .. py:attribute:: environment
      :type: Optional


   .. py:attribute:: root_domain
      :type: Optional


   .. py:attribute:: api_key
      :type: Optional

      The top-level api_key, used by any environment.


   .. py:attribute:: api_keys
      :type: dict

      The api key of each environment.


   .. py:method:: load(path: pathlib.Path) -> 'CliConfig'
      :classmethod:

      Read the cli's configuration file.

      A missing or unreadable file is an empty configuration: the file is optional.

      :param path: The file's path.
      :returns: The configuration.



.. py:class:: ClientConfig

   Bases: :class:`pydantic.main.BaseModel`

   A client's resolved configuration.

   .. py:attribute:: api_key
      :type: SecretStr


   .. py:attribute:: base_url
      :type: str

      The api's base url, ending in /api/v1/.


   .. py:attribute:: environment
      :type: Literal


   .. py:attribute:: timeout
      :type: float


   .. py:attribute:: max_retries
      :type: int



.. py:function:: environment_url(environment: Literal['local', 'alpha', 'beta', 'next', 'prod'], root_domain: str) -> str

   The platform url of an environment, as the smarter cli derives it.

   :param environment: The environment.
   :param root_domain: The platform's root domain, e.g. ``platform.smarter.sh``.
   :returns: e.g. ``https://alpha.platform.smarter.sh``.

.. py:function:: api_base_url(url: str) -> str

   The api's base url for a platform url.

   ``https://example.com`` and ``https://example.com/api/v1`` both become
   ``https://example.com/api/v1/``.

   :param url: A platform url, with or without the api's path.
   :returns: The url, with the api's path and a trailing slash.
   :raises SmarterConfigurationError: If the url is not an http or https url.

.. py:function:: resolve_client_config(*, api_key: Optional[str] = None, base_url: Optional[str] = None, environment: Optional[Literal['local', 'alpha', 'beta', 'next', 'prod']] = None, timeout: Optional[float] = None, max_retries: Optional[int] = None, settings: Optional[smarter.core.conf.SmarterSettings] = None) -> smarter.core.conf.ClientConfig

   Resolve a client's configuration from its arguments, the environment, and the cli's configuration file.

   :param api_key: The api key, or None to look it up.
   :param base_url: The platform's url, or None to derive it from the environment.
   :param environment: The environment, or None to look it up.
   :param timeout: The request timeout in seconds, or None for the setting.
   :param max_retries: How many times to retry a failed request, or None for the setting.
   :param settings: The settings to use instead of reading the environment variables, for tests.
   :returns: The configuration.
   :raises SmarterConfigurationError: If no api key is found, or the base url is invalid.

``smarter.core.exceptions``
---------------------------

.. py:module:: smarter.core.exceptions

The exceptions of the Smarter Python SDK.

Every exception that the SDK raises is a :class:`SmarterError`, so a caller can catch them all with
one ``except`` clause. This follows the Smarter platform's own rule (ADR-012) that exceptions
subclass one hierarchy.

The api errors mirror the http status that the Smarter api returned:

.. code-block:: text

    SmarterError
    ├── SmarterConfigurationError        the client has no api key or base url
    ├── SmarterValueError                an argument is invalid, before any request is sent
    ├── ResourceNotFoundError            a resource was not found, by the api (NotFoundError) or by find()
    └── APIError
        ├── APIConnectionError           the request never got a response
        │   └── APITimeoutError
        ├── APIResponseValidationError   the response does not match the SDK's model of it
        └── APIStatusError               the api returned a 4xx or 5xx status
            ├── BadRequestError          400
            ├── AuthenticationError      401
            ├── PermissionDeniedError    403
            ├── NotFoundError            404, also a ResourceNotFoundError
            ├── ConflictError            409
            ├── UnprocessableEntityError 422
            ├── RateLimitError           429
            └── InternalServerError      5xx

.. py:class:: SmarterError

   Bases: :class:`builtins.Exception`

   The base class of every exception that the Smarter SDK raises.


.. py:class:: SmarterConfigurationError

   Bases: :class:`smarter.core.exceptions.SmarterError`

   The client is missing configuration that it needs, e.g. an api key or a base url.


.. py:class:: SmarterValueError

   Bases: :class:`smarter.core.exceptions.SmarterError`, :class:`builtins.ValueError`

   An argument is invalid.

   Raised before a request is sent.


.. py:class:: ResourceNotFoundError

   Bases: :class:`smarter.core.exceptions.SmarterError`, :class:`builtins.LookupError`

   A resource was not found: the api answered 404 (:class:`NotFoundError`), or ``find()`` found no resource of that name.


.. py:class:: APIError(message: str, request: httpx.Request, *, body: object = None) -> None

   Bases: :class:`smarter.core.exceptions.SmarterError`

   A request to the Smarter api failed.

   :param message: A human-readable description of the error.
   :param request: The http request that failed.
   :param body: The response's parsed JSON body, or its text, or None when there is no response.


.. py:class:: APIConnectionError(request: httpx.Request, message: str = 'Connection error.') -> None

   Bases: :class:`smarter.core.exceptions.APIError`

   The request did not get a response, e.g. the server is unreachable.


.. py:class:: APITimeoutError(request: httpx.Request) -> None

   Bases: :class:`smarter.core.exceptions.APIConnectionError`

   The request timed out.


.. py:class:: APIResponseValidationError(response: httpx.Response, body: object, message: str) -> None

   Bases: :class:`smarter.core.exceptions.APIError`

   The api's response does not match the SDK's model of it.

   This usually means that the SDK and the Smarter platform are of incompatible versions.

   :param response: The http response.
   :param body: The response's parsed JSON body.
   :param message: A description of the mismatch.


.. py:class:: APIStatusError(message: str, *, response: httpx.Response, body: object, error: Optional[ForwardRef('SAMJournalApiErrorBody')] = None) -> None

   Bases: :class:`smarter.core.exceptions.APIError`

   The api returned a 4xx or 5xx status.

   :param message: The error's description, from the response when it has one.
   :param response: The http response.
   :param body: The response's parsed JSON body, or its text.
   :param error: The Smarter Journal error body, when the response is a journaled error.

   .. py:property:: error_class

      The name of the server-side exception class, e.g. ``SAMBrokerErrorNotFound``, when the platform sent it.



.. py:class:: BadRequestError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   400: the request is invalid, e.g. a malformed manifest.


.. py:class:: AuthenticationError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   401: the api key is missing, invalid, or inactive.


.. py:class:: PermissionDeniedError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   403: the api key's user may not perform the operation.


.. py:class:: NotFoundError

   Bases: :class:`smarter.core.exceptions.APIStatusError`, :class:`smarter.core.exceptions.ResourceNotFoundError`

   404: the resource does not exist, or the api key's user may not read it.


.. py:class:: ConflictError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   409: the request conflicts with the resource's current state.


.. py:class:: UnprocessableEntityError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   422: the request is well-formed but cannot be processed.


.. py:class:: RateLimitError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   429: too many requests.


.. py:class:: InternalServerError

   Bases: :class:`smarter.core.exceptions.APIStatusError`

   5xx: the platform failed to process the request.


``smarter.core.http``
---------------------

.. py:module:: smarter.core.http

The SDK's http transport: authentication, retries, error mapping, and response parsing.

:class:`SmarterHttpClient` sends every request of a :class:`smarter.Smarter` client. It adds the
api key and the SDK's headers, retries requests that failed for transient reasons, raises a
:mod:`smarter.core.exceptions` error for a 4xx or 5xx response, and validates the response's
JSON against a Pydantic model.

.. py:data:: QueryParamValue

   A query parameter's value.

   None leaves the parameter out.

.. py:data:: CLIENT_NAME

   The SDK's ``X-Smarter-Client`` header, which identifies it to the platform's logs and journal.

.. py:function:: parse_body(response: httpx.Response) -> object

   A response's body: its JSON, or its text when it is not JSON.

   :param response: The response, which must have been read.
   :returns: The parsed JSON, the text, or None for an empty body.

.. py:function:: journal_error(body: object) -> Optional[smarter.models.journal.SAMJournalApiErrorBody]

   The Smarter Journal error of a response body, if it is a journaled error response.

   :param body: A parsed response body.
   :returns: The error body, or None.

.. py:function:: error_message(response: httpx.Response, body: object, error: Optional[smarter.models.journal.SAMJournalApiErrorBody]) -> str

   A human-readable message for an error response.

   The platform's views return errors in several shapes: the journal's ``error`` object, an
   ``error`` string, Django REST framework's ``detail``, plain text, or a Django error page.

   :param response: The response.
   :param body: Its parsed body.
   :param error: Its journal error, if any.
   :returns: The message.

.. py:function:: make_status_error(response: httpx.Response) -> smarter.core.exceptions.APIStatusError

   The exception for a 4xx or 5xx response, by its status.

   :param response: The response, which must have been read.
   :returns: e.g. a :class:`~smarter.core.exceptions.NotFoundError` for a 404.

.. py:function:: is_retryable(response: httpx.Response) -> bool

   True if a failed response may succeed when the request is sent again.

   A 503 is retried only when it is not a journaled response. The Smarter platform itself answers
   503 for a resource that is not ready (e.g. ``SAMBrokerErrorNotReady``), which a retry won't
   change, whereas a 503 from a load balancer or proxy means the platform is briefly unavailable.

   :param response: The response, which must have been read.
   :returns: True to retry.

.. py:function:: retry_delay(attempt: int, response: Optional[httpx.Response] = None) -> float

   Seconds to wait before a retry: the response's ``Retry-After``, or exponential backoff with jitter.

   :param attempt: The number of the attempt that failed, from 0.
   :param response: The failed response, if there was one.
   :returns: The delay.

.. py:function:: query_params(params: Optional[collections.abc.Mapping[str, Union[str, int, float, bool, NoneType]]]) -> dict[str, str]

   Query parameters as strings: booleans as ``true`` or ``false``, and None values left out.

   :param params: The parameters.
   :returns: The parameters that httpx sends.

.. py:class:: SmarterHttpClient(config: smarter.core.conf.ClientConfig, *, default_headers: Optional[collections.abc.Mapping[str, str]] = None, http_client: Optional[httpx.Client] = None) -> None

   Sends the requests of a Smarter client.

   :param config: The client's resolved configuration.
   :param default_headers: Headers to add to every request.
   :param http_client: An ``httpx.Client`` to use, e.g. with a proxy or a test transport. Its own
       base url and timeout are ignored.

   .. py:property:: base_url

      The api's base url, e.g. ``https://platform.smarter.sh/api/v1/``.


   .. py:property:: max_retries

      How many times a failed request is retried.


   .. py:method:: url(path: str) -> str

      The absolute url of an api path.

      :param path: A path relative to the base url, e.g. ``cli/whoami/``. An absolute url is returned as is.
      :returns: The url.


   .. py:method:: headers(extra: Optional[collections.abc.Mapping[str, str]] = None) -> dict[str, str]

      The headers of a request.

      :param extra: Headers for this request, which override the defaults.
      :returns: The headers.


   .. py:method:: build_request(method: str, path: str, *, params: Optional[collections.abc.Mapping[str, Union[str, int, float, bool, NoneType]]] = None, json: object = None, content: Union[str, bytes, NoneType] = None, files: Optional[collections.abc.Mapping[str, Any]] = None, data: Optional[collections.abc.Mapping[str, Any]] = None, headers: Optional[collections.abc.Mapping[str, str]] = None, timeout: Optional[float] = None) -> httpx.Request

      Build a request.

      See :meth:`request` for the parameters.

      :returns: The request.


   .. py:method:: send(request: httpx.Request, *, stream: bool = False) -> httpx.Response

      Send a request, with retries, and raise for an error status.

      :param request: The request.
      :param stream: True to return before the body is read, for Server-Sent Events. The caller
          must close the response.
      :returns: The successful response.
      :raises APIConnectionError: If no response was received after the retries.
      :raises APITimeoutError: If the request timed out after the retries.
      :raises APIStatusError: For a 4xx or 5xx response, as the status's subclass.


   .. py:method:: request(method: str, path: str, *, cast_to: Any, params: Optional[collections.abc.Mapping[str, Union[str, int, float, bool, NoneType]]] = None, json: object = None, content: Union[str, bytes, NoneType] = None, files: Optional[collections.abc.Mapping[str, Any]] = None, data: Optional[collections.abc.Mapping[str, Any]] = None, headers: Optional[collections.abc.Mapping[str, str]] = None, timeout: Optional[float] = None) -> Any

      Send a request, and validate its JSON response.

      :param method: The http method, e.g. ``GET``.
      :param path: The path, relative to the api's base url, e.g. ``guardrails/``.
      :param cast_to: The type of the response's JSON, e.g. ``Guardrail`` or ``list[Guardrail]``.
          ``None`` ignores the body.
      :param params: Query parameters.
      :param json: A JSON body.
      :param content: A raw body, e.g. a YAML manifest.
      :param files: Files, for a multipart/form-data body.
      :param data: Form fields, for a multipart/form-data body.
      :param headers: Headers for this request.
      :param timeout: The timeout in seconds, instead of the client's.
      :returns: The validated response, an instance of ``cast_to``.
      :raises APIResponseValidationError: If the response does not match ``cast_to``.


   .. py:method:: stream_events(method: str, path: str, *, json: object = None, headers: Optional[collections.abc.Mapping[str, str]] = None, timeout: Optional[float] = None) -> collections.abc.Iterator[collections.abc.Iterator[smarter.core.streaming.ServerSentEvent]]

      Send a request that asks for Server-Sent Events, and iterate its events.

      .. code-block:: python

          with http.stream_events("POST", "llm-clients/5/prompt/", json=body) as events:
              for event in events:
                  ...

      :param method: The http method.
      :param path: The path, relative to the api's base url.
      :param json: A JSON body.
      :param headers: Headers for this request.
      :param timeout: The timeout in seconds, instead of the client's. It applies to each read.
      :returns: A context manager whose value iterates the events. The response is closed on exit.


   .. py:method:: close() -> None

      Close the underlying ``httpx.Client``, unless it was passed in by the caller.



``smarter.core.streaming``
--------------------------

.. py:module:: smarter.core.streaming

A parser of Server-Sent Events.

The Smarter prompt api streams a prompt's progress as Server-Sent Events when the request's
``Accept`` header includes ``text/event-stream``: ``progress`` events while it runs, then one
``result`` event with the same JSON as a non-streaming response.

.. py:class:: ServerSentEvent(event: Optional[str], data: str, id: Optional[str] = None, retry: Optional[int] = None) -> None

   One Server-Sent Event.

   :param event: The event's type, e.g. ``progress``, or None for an unnamed event.
   :param data: The event's data: its ``data:`` lines, joined by newlines.
   :param id: The event's id, if any.
   :param retry: The reconnection time that the server asked for, in milliseconds, if any.

   .. py:method:: json() -> JsonValue

      The event's data, parsed as JSON.

      :returns: The parsed data.
      :raises json.JSONDecodeError: If the data is not JSON.



.. py:function:: iter_sse(lines: collections.abc.Iterable[str]) -> collections.abc.Iterator[smarter.core.streaming.ServerSentEvent]

   Parse a stream's lines into events, as the HTML Living Standard specifies.

   A blank line ends an event. Comments (lines that start with ``:``), and blocks that set only
   ``retry``, yield nothing.

   :param lines: The stream's lines, without their line endings.
   :returns: The events, in order.

``smarter.core.log``
--------------------

.. py:module:: smarter.core.log

Logging for the Smarter SDK.

The SDK logs to the ``smarter`` logger hierarchy (``smarter.client``, ``smarter.resources...``) and,
as a library should, adds no handlers unless asked to. Set ``SMARTER_LOG=info`` to log each
request's method, url, status and duration to stderr, or ``SMARTER_LOG=debug`` to log their bodies
too. Or configure the ``smarter`` logger as you would any other.

The Smarter platform controls its logging per module with waffle switches (ADR-011). The SDK's
equivalent is the logger hierarchy: e.g. ``logging.getLogger("smarter.client").setLevel(...)``.

Api keys are never logged: see :func:`mask_secret`.

.. py:function:: mask_secret(secret: Optional[str]) -> str

   A secret, masked for logging: its last four characters.

   :param secret: The secret, e.g. an api key.
   :returns: e.g. ``****5150``, or ``None``.

.. py:function:: setup_logging(level: Optional[str]) -> None

   Log the SDK's messages to stderr, at the given level, once per process.

   :param level: ``debug`` or ``info``, or None to leave logging as it is.

``smarter.core.typing``
-----------------------

.. py:module:: smarter.core.typing

Type aliases of the Smarter SDK.

These mirror ``smarter.lib.typing`` in the Smarter platform. This module imports only from the
standard library and pydantic, so that any module of the SDK can import it without an import cycle.

.. py:data:: SmarterDictType

   A mapping whose values really can be of any type.

   Prefer a Pydantic model when the shape is known.

.. py:data:: SmarterJsonType

   A value that is arbitrary JSON: a string, number, boolean, null, or a list or object of them.

.. py:data:: SmarterJsonObjectType

   A JSON object whose shape is not fixed, e.g. a manifest's ``spec``, whose fields depend on its kind.

.. py:data:: SmarterIdType

   A resource's id: its integer primary key, or its hashed id, e.g. ``rMTAwMDAwNQx``.
