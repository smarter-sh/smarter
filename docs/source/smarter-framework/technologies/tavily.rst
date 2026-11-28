Tavily Web Search
=================

`Tavily <https://tavily.com>`_ is a commercial web search API that is designed for LLMs and
AI agents. Like a search engine, it takes a query and returns ranked web pages, but each result
is returned as structured json (a title, a url, a snippet of the page's content, and its
publication date) rather than as a page of links for a person to read. This makes it a good fit
for tool calling, where the LLM reads the results and cites them.

Smarter uses Tavily as one of the two web search APIs of the
:doc:`WebsearchPlugin <../../smarter-resources/llmtool/plugin/websearch>`. The other is the
`Brave Search API <https://brave.com/search/api/>`_. Each WebsearchPlugin chooses its search API
in its manifest.

.. note::

    The WebsearchPlugin is experimental. See
    :doc:`WebsearchPlugin <../../smarter-resources/llmtool/plugin/websearch>`.


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
:py:class:`smarter.apps.llmtool.plugin.websearch_providers.TavilySearchProvider`.

**The sample WebsearchPlugin.** ``smarter_project_websearch`` uses Tavily to find current
information about The Smarter Project on the web, from reputable sources. It is an example to
copy, and no example LLMClient uses it. Its manifest is
`plugins/websearch/websearch-smarter-project.yaml
<https://github.com/smarter-sh/example-manifests/blob/main/smarter/plugins/websearch/websearch-smarter-project.yaml>`__,
in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.

``manage.py initialize_platform`` and ``manage.py initialize_account`` apply the sample plugins,
with ``manage.py load_from_github``. Applying ``smarter_project_websearch`` fails if its Secret
``tavily_api_key`` does not exist. The other plugins are not affected: each manifest is applied in
its own transaction, so a manifest that fails is rolled back entirely, and is reported, and the
command goes on to the next one.

Setup
-----

1. **Get an API key.** Create an account at `tavily.com <https://tavily.com>`_, and copy an API
   key from its dashboard. Tavily keys begin with ``tvly-``.

2. **Add it to the platform's bootstrap secrets.** The key is never an environment variable: its
   only source is the Smarter Secret ``tavily_api_key``, owned by the smarter admin. For local
   development, write it into a file of that name in the repository's gitignored
   ``bootstrap-secrets/`` folder, which ``.env.example`` documents. On Kubernetes, set the Helm
   chart's ``bootstrapSecrets.tavily_api_key`` instead.

   .. code-block:: bash

       printf %s 'tvly-...' > bootstrap-secrets/tavily_api_key

3. **Create the Secret.** ``manage.py initialize_bootstrap_secrets``, which ``manage.py
   initialize_platform`` runs, stores the file's key as the Secret ``tavily_api_key``. It updates
   the Secret when the key has changed, so running it again rotates the key.

   .. code-block:: bash

       python manage.py initialize_platform

   An empty file, or one that still holds a placeholder, such as ``SET-ME-PLEASE``, is skipped: the
   command never stores a placeholder as the key. ``manage.py initialize_llmtool_api_keys``, which
   ``initialize_platform`` runs next, then lists the Secret in the ``[API KEYS NOT SET]`` console
   error that it logs, with the other missing API keys. An admin can also set the Secret in the web
   console, or with ``smarter apply``.

4. **Apply the sample plugins.**

   .. code-block:: bash

       python manage.py load_from_github --url https://github.com/smarter-sh/example-manifests --include_kind WebsearchPlugin

Other WebsearchPlugins can use the same Secret, by setting ``apiKey: tavily_api_key``, or a
Secret of their own: ``apiKey`` is the name of any Secret that the plugin's owner can read. See
the sample manifests in `plugins/websearch/
<https://github.com/smarter-sh/example-manifests/tree/main/smarter/plugins/websearch>`__.

The environment variable is listed in :doc:`Configuration <../../smarter-platform/configuration>`.


CI/CD Considerations
--------------------

**GitHub repository secret.** Both workflows read the key from the GitHub Actions repository
secret ``TAVILY_API_KEY``. Add it in the repository's *Settings > Secrets and variables >
Actions*. It is never committed: neither ``values.yaml`` nor any manifest contains the key.

**Tests (.github/workflows/test.yml).** The workflow writes the secret, with the other API keys,
into ``bootstrap-secrets/tavily_api_key``, with ``scripts/bootstrap_secrets.py``, never into the
test containers' ``.env``. The unit tests do not call Tavily: they serve the
Tavily API from a fake web host, and create a test Secret, so they pass without the GitHub
secret.

**Deployments (.github/workflows/deploy.yml).** The workflow passes the GitHub secret to the
``tavily-api-key`` input of ``.github/actions/deploy``, which sets the Helm value
``bootstrapSecrets.tavily_api_key``. The chart puts it in the Kubernetes Secret
``smarter-bootstrap-secrets``, which only the init Job mounts. The init Job,
``templates/job-init.yaml``, is a Helm ``post-install`` and ``post-upgrade`` hook, so every
deployment runs ``initialize_platform``, which creates or updates the Secret, and applies the
sample plugins. Consequently:

- **Adding the key** to an existing installation takes effect on the next deployment.
- **Rotating the key**: update the GitHub secret, and deploy. The Secret is updated in place.
- **A deployment without the key** completes, but the init Job logs that the ``tavily_api_key``
  Secret does not exist, and that ``smarter_project_websearch`` could not be applied. When the
  GitHub secret is not set, the deploy action leaves ``tavily_api_key`` out of
  ``bootstrapSecrets``, and an existing Secret is kept.
- **Every environment** that uses a Tavily WebsearchPlugin needs the key: local, alpha, beta
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
    The plugin was applied before the Secret existed, or by a user who cannot read it. Write
    ``bootstrap-secrets/tavily_api_key``, run ``manage.py initialize_platform``, and apply the plugin again.

``Plugin smarter_project_websearch not found for account ...``
    An LLMClient that names the plugin was applied, but the plugin was not, almost always because
    of the missing Secret above. Fix the Secret, apply the plugin again, e.g. with ``manage.py
    load_from_github --include_kind WebsearchPlugin``, and apply the LLMClient again.

``The Secret tavily_api_key does not exist``, and ``tavily_api_key`` in the ``[API KEYS NOT SET]`` console error
    The platform's bootstrap secrets held no key, or only a placeholder. Write
    ``bootstrap-secrets/tavily_api_key``, or, in a deployment, set the GitHub secret ``TAVILY_API_KEY``.
