Tavily Web Search
=================

`Tavily <https://tavily.com>`_ is a commercial web search API that is designed for LLMs and
AI agents. Like a search engine, it takes a query and returns ranked web pages, but each result
is returned as structured json (a title, a url, a snippet of the page's content, and its
publication date) rather than as a page of links for a person to read. This makes it a good fit
for tool calling, where the LLM reads the results and cites them.

Smarter uses Tavily as one of the two web search APIs of the
:doc:`WebsearchPlugin <../../smarter-resources/plugin/plugin/websearch>`. The other is the
`Brave Search API <https://brave.com/search/api/>`_. Each WebsearchPlugin chooses its search API
in its manifest.

.. note::

    The WebsearchPlugin is experimental. See
    :doc:`WebsearchPlugin <../../smarter-resources/plugin/plugin/websearch>`.


How Smarter Uses Tavily
-----------------------

**The WebsearchPlugin.** A WebsearchPlugin gives an LLM one tool with two operations: search the
web, and read a web page. Only search uses Tavily. When the LLM sets a ``query``, the plugin
sends it to the Tavily Search API, ``https://api.tavily.com/search``, and returns the results to
the LLM in the same form as Brave's, so that the LLM sees the same fields whichever API is
configured. Reading a web page, the fetch operation, is done by Smarter itself, not by Tavily.

The plugin's manifest selects Tavily, and names the Smarter
:doc:`Secret <../../smarter-resources/smarter-secret>` that contains the Tavily API key:

.. code-block:: yaml

    spec:
      websearchData:
        search:
          provider: tavily
          apiKey: tavily_api_key    # the name of a Smarter Secret, never the key itself
          maxResults: 5
          safeSearch: moderate
        blockedDomains:
          - pinterest.com

Each search request:

- uses Tavily's ``basic`` search depth and ``general`` topic, and asks for no generated answer
  and no raw page content, only ranked results.
- passes the plugin's ``allowedDomains`` and ``blockedDomains`` to Tavily, as its
  ``include_domains`` and ``exclude_domains``. Smarter also filters the results that Tavily
  returns by the same domain policy, so that the policy is enforced even if Tavily returns a
  result that it should not.
- passes ``safeSearch`` as Tavily's ``safe_search``, which is either on or off: ``moderate`` and
  ``strict`` both turn it on.
- passes ``freshness`` (day, week, month or year) and ``language``. The plugin's ``country`` is
  not passed, because Tavily localizes by country name rather than by country code.

Search results are cached, per plugin, for the manifest's ``cacheTtl`` seconds, keyed on the
query and its parameters. A repeated question does not call Tavily again until the cache
expires.

The implementation is
:py:class:`smarter.apps.plugin.plugin.websearch_providers.TavilySearchProvider`.

**The smarter LLMClient.** The platform's built-in ``smarter`` LLMClient, the Smarter sales
agent, uses the built-in WebsearchPlugin ``smarter_project_websearch`` to find current
information about The Smarter Project on the web, from reputable sources. It complements the
documentation and source code that its ``smarter_project_github`` MCPClients read. Its manifests are in
the source tree:

- ``smarter/smarter/apps/llmclient/data/plugins/plugin-smarter-websearch.yaml``
- ``smarter/smarter/apps/llmclient/data/llm-clients/llmclient-smarter.yaml``

``manage.py deploy_builtin_llmclients`` applies the built-in plugins, and then the built-in
LLMClients. Applying an LLMClient fails if any plugin that it names does not exist, and applying
``smarter_project_websearch`` fails if its Secret ``tavily_api_key`` does not exist. **An
installation without a Tavily API key therefore cannot deploy the smarter LLMClient.** The other
built-in plugins and LLMClients are not affected: the command applies each manifest in its own
transaction, so a manifest that fails is rolled back entirely, and is reported, and the command
goes on to the next one. An existing smarter LLMClient keeps its previous version.


Setup
-----

1. **Get an API key.** Create an account at `tavily.com <https://tavily.com>`_, and copy an API
   key from its dashboard. Tavily keys begin with ``tvly-``.

2. **Set the environment variable.** Set ``TAVILY_API_KEY``. As with every Smarter setting, the
   name may also be given the ``SMARTER_`` prefix, ``SMARTER_TAVILY_API_KEY``: the two are the
   same setting. For local development, add it to ``.env``, which ``.env.example`` documents:

   .. code-block:: bash

       SMARTER_TAVILY_API_KEY=tvly-...

3. **Create the Secret.** ``manage.py initialize_providers``, which ``manage.py
   initialize_platform`` runs, stores the key as the Smarter Secret ``tavily_api_key``, owned by
   the smarter admin. It updates the Secret if it already exists, so running it again rotates
   the key.

   .. code-block:: bash

       python manage.py initialize_providers

   If ``TAVILY_API_KEY`` is not set, or is still a placeholder, such as ``.env.example``'s
   ``SET-ME-PLEASE`` or ``values.yaml``'s ``SET-ME-IN-helm/charts/smarter/values.yaml``, the
   command logs a warning and does not create the Secret. It never stores a placeholder as the
   key.

4. **Deploy the built-in LLMClients.**

   .. code-block:: bash

       python manage.py deploy_builtin_llmclients --account_number 3141-5926-5359

Other WebsearchPlugins can use the same Secret, by setting ``apiKey: tavily_api_key``, or a
Secret of their own: ``apiKey`` is the name of any Secret that the plugin's owner can read. See
the sample manifests in ``smarter/smarter/apps/plugin/data/sample-plugins/websearch-*.yaml``.

The environment variable is listed in :doc:`Configuration <../../smarter-platform/configuration>`.


CI/CD Considerations
--------------------

**GitHub repository secret.** Both workflows read the key from the GitHub Actions repository
secret ``TAVILY_API_KEY``. Add it in the repository's *Settings > Secrets and variables >
Actions*. It is never committed: neither ``values.yaml`` nor any manifest contains the key.

**Tests (.github/workflows/test.yml).** The workflow passes ``TAVILY_API_KEY`` to the test
containers' ``.env``, with the other API keys. The unit tests do not call Tavily: they serve the
Tavily API from a fake web host, and create a test Secret, so they pass without the GitHub
secret.

**Deployments (.github/workflows/deploy.yml).** The workflow passes the GitHub secret to the
``tavily-api-key`` input of ``.github/actions/deploy``, which sets the Helm value
``env.SMARTER_TAVILY_API_KEY``. The chart's init Job, ``templates/job-init.yaml``, is a Helm
``post-install`` and ``post-upgrade`` hook, so every deployment runs ``initialize_platform``,
which creates or updates the Secret, and then ``deploy_builtin_llmclients``. Consequently:

- **Adding the key** to an existing installation takes effect on the next deployment.
- **Rotating the key**: update the GitHub secret, and deploy. The Secret is updated in place.
- **A deployment without the key** completes, but the init Job logs that the ``tavily_api_key``
  Secret was not created, and that ``smarter_project_websearch``, and therefore the ``smarter``
  LLMClient, could not be applied. The other built-in LLMClients are applied as usual. When the
  GitHub secret is not set, the deploy action passes no value, and Helm falls back to the
  ``values.yaml`` placeholder, which the init command recognizes and ignores.
- **Every environment** that deploys the built-in LLMClients needs the key: local, alpha, beta
  and production. Each may use its own Tavily key, for separate usage and billing.


Cost and Limits
---------------

Tavily bills by API credits, and offers a free plan with a monthly allowance of credits; see
the pricing on `tavily.com <https://tavily.com>`_. Smarter keeps usage low:

- every search uses the ``basic`` search depth, Tavily's least expensive.
- results are cached for the plugin's ``cacheTtl``. ``smarter_project_websearch`` caches them for
  a day, because information about the project changes slowly.
- only search calls Tavily. Reading a web page does not.

Monitor usage in the Tavily dashboard. When Tavily refuses a search, for example because the key
is invalid or out of credits, the WebsearchPlugin returns an error to the LLM instead of search
results, and sends the ``websearch_failed`` signal.


Troubleshooting
---------------

``the web search api key Secret tavily_api_key does not exist, or is not accessible``
    The plugin was applied before the Secret existed, or by a user who cannot read it. Set
    ``TAVILY_API_KEY``, run ``manage.py initialize_providers``, and apply the plugin again.

``Plugin smarter_project_websearch not found for account ...``
    The smarter LLMClient was applied, but its WebsearchPlugin was not, almost always because of
    the missing Secret above. Fix the Secret, and run ``manage.py deploy_builtin_llmclients``,
    which reports each manifest that it fails to apply as ``Failed to apply manifest ...``.

``initialize_tavily: TAVILY_API_KEY is not set``
    The init command found no key, or only a placeholder. Set the environment variable, or, in a
    deployment, the GitHub secret ``TAVILY_API_KEY``.
