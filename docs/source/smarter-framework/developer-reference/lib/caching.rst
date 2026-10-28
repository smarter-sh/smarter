Smarter Caching
=================

Smarter caches in Redis with :func:`~cache_results.decorators.cache_results`, which caches a function's
result under a key built from its module, qualified name and arguments, and gives the function an
``invalidate()``. It decorates regular functions, ``async`` functions and classmethods, but refuses
instance methods, because ``self`` would be part of the key. Concurrent callers in one process that
miss the same key wait for the first to compute it, and calls made before Django's apps are ready run
uncached. ``async`` functions read and write the cache without blocking the event loop. Its logs
name the cached function and the type of its result, never the result itself.

Arguments must be plain values: strings, numbers, booleans, ``None``, and lists, tuples, dicts and
sets of them, plus datetimes, Decimals, UUIDs, classes, dataclasses and Pydantic models. Any other
argument, such as a model instance, runs the function uncached and logs an error that names the
function and the argument's type, once per process. Pass the instance's id instead. ``str()`` of an
object is never used as a key: two rows with the same name would share an entry, and an object
without its own ``__str__`` would have a new key in every process.

The decorator is the standalone package `cache-results <https://pypi.org/project/cache-results/>`__,
which depends only on Django and is published under the MIT license, with its own documentation at
`docs.cache-results.smarter.sh <https://docs.cache-results.smarter.sh/>`__. Smarter installs it from
PyPI, and code imports it as ``from cache_results import cache_results``. Raw ``get()`` and ``set()``
go through the package's :data:`~cache_results.lazy.lazy_cache`, Django's cache imported only
once Django is ready, never through ``django.core.cache``. The ``CACHE_RESULTS`` setting (see
:mod:`cache_results.conf`) names the cache alias, the default timeout, a key prefix and version that can
abandon every cached result at once, the key encoder, and the logging hooks.
:mod:`smarter.lib.cache.hooks` connects them to Smarter: the default timeout is
``smarter_settings.cache_expiration``, logging follows the ``CACHE_LOGGING`` waffle switch, the
key encoder accepts Pydantic models, and the package's :func:`~cache_results.colors.log_prefix`
colors log messages. These hooks stay in Smarter because they need Pydantic, django-waffle and
Smarter's settings, which the package doesn't depend on.

The web console's resource lists build on it: each list api caches its pages per user, the React
lists keep the pages they showed in the browser, and saving or deleting a resource makes its list's
cached pages stale at once. See :doc:`django/listview`.

Tool Calls and Prompts
----------------------

A prompt that calls tools spends most of its time waiting for them: an MCP server, a web search,
a database. So Smarter caches the result of every tool call that can be cached, for about an hour,
by the tool and its arguments, whichever LLMClient or conversation makes the call. Every kind of
tool caches through one function, :func:`smarter.lib.cache.tool_results.cached_tool_call`, which
owns the rules: the key is the kind of tool, what identifies it, and its arguments as canonical
JSON; a result is JSON, so it can be shared; an error is never stored, whether the tool raises it
or returns it (``Error: ...`` text, or an object with an ``error`` key); and a timeout of 0 skips
the cache. Each kind decides only what
may be cached and for how long:

- **MCP servers.** The results of the tools that an MCP server marks read-only (``readOnlyHint``),
  and of resource reads, are cached for the MCPClient's ``cacheTtl``, an hour by default. Other
  tools may change something, so they are called every time.
- **Plugins.** Each plugin caches its remote calls: an ApiPlugin's GET requests and a SqlPlugin's
  queries for an hour, web searches for their manifest's ``cacheTtl``. See
  :class:`smarter.apps.llmtool.const.PluginCacheTtl`.
- **Extensions.** A tool that sets
  :attr:`~smarter.apps.llmtool.extension.protocol.SmarterExtensionTool.cache_ttl` has its results
  cached, by its arguments and the Extension's settings. Extension tools can depend on who calls
  them, so the default is no caching.
- **The Smarter Project MCP server** caches its own tool results for an hour, until a repository is
  indexed again. See :mod:`smarter.apps.mcpserver.caching`.

The LLM's answer to the first message of a conversation is cached too, for
``smarter_settings.prompt_response_cache_expiration`` seconds (``SMARTER_PROMPT_RESPONSE_CACHE_EXPIRATION``,
an hour by default, 0 to disable). A first message has no conversation before it, so the same
message, sent to the same LLMClient, gets the same answer, and the LLMClient's
``appExamplePrompts`` arrive word for word. The key is a hash of the message, normalized for case,
whitespace and trailing punctuation, with the LLMClient, when it last changed, its provider, model
and settings. A cached answer is returned without calling the LLM or its tools, and costs no tokens.
Later messages are never cached, because their answers depend on the conversation, and a first
message whose LLM called a tool that can't be cached, or failed, isn't either. See
:mod:`smarter.apps.provider.services.text_completion.lib.prompt_cache`.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   caching/hooks
   caching/tool-results
