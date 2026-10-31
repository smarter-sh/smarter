The Example Manifests Repository
================================

Every Smarter platform starts with a library of example resources, so that there is something to
explore, copy and learn from on a fresh installation: LLMClients that range from a bare model to a
completely styled, governed application, plugins of every kind, guardrails, MCP clients, Proxies,
self-hosted models, vector stores and budgets. Their manifests are not part of the Smarter
platform. They live in their own community-supported GitHub repository,
`smarter-sh/example-manifests <https://github.com/smarter-sh/example-manifests>`__, where anyone
can read them, copy them into a project of their own, and propose new ones.

The Repository
--------------

Each folder holds the manifests of one kind of resource.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Folder
     - Resources
   * - ``llm-clients/``
     - :doc:`LLMClients </smarter-resources/smarter-llmclient>`, e.g. ``simple``, ``calculator``,
       ``weather``, ``research_analyst``, ``data_analyst`` and ``customer_support``.
   * - ``plugins/static/``, ``plugins/skill/``, ``plugins/websearch/``, ``plugins/image-search/``
     - :doc:`Plugins </smarter-resources/smarter-llmtool>`: Static, Skill, Websearch and ImageSearch
       plugins.
   * - ``guardrails/``
     - :doc:`Guardrails </smarter-resources/smarter-guardrail>` for inputs and outputs.
   * - ``mcp-clients/``
     - :doc:`MCPClients </smarter-resources/smarter-mcpclient>` for public MCP servers, and, as
       :doc:`manifest templates <manifest-templates>`, ``*.yaml.tpl``, for the
       :doc:`Smarter Project MCP server </smarter-platform/smarter-project-mcp-server>`.
   * - ``proxies/``
     - :doc:`Proxies </smarter-resources/smarter-proxy>`, one per built-in Provider.
   * - ``llmhosts/``, ``llmhost-computes/``
     - :doc:`LLMHosts </smarter-resources/smarter-llmhost>`, self-hosted open-weight models, and the
       LLMHostCompute node groups that they run on.
   * - ``vectorstores/``
     - :doc:`VectorStores </smarter-resources/smarter-vectorstore>`.
   * - ``custom-domains/``
     - A :doc:`CustomDomain </smarter-resources/smarter-custom-domain>`, ``example.com``.
   * - ``budgets/``
     - :doc:`Budgets </smarter-resources/smarter-budget>`. Each is detached, ``resources: []``, with
       the resources that it could be attached to as a commented-out example.

Its pre-commit hooks check every manifest against the JSON Schema of its kind, which the Smarter
platform publishes, before each commit, and a GitHub Actions workflow runs them on every pull request.

How a Platform Loads It
-----------------------

``manage.py load_from_github`` clones a GitHub repository of manifests and applies each of them, in
the order of their kinds' dependencies, :meth:`SAMKinds.apply_order()
<smarter_types.kinds.SAMKinds.apply_order>`. Some examples need a resource that
only the platform's operator can create, e.g. the Secret that holds an MCPClient's access token
for a third-party service, or the ApiConnection of a managed vector database. With
``--skip_missing_references``, which both initialization commands pass, such a manifest is skipped,
with a warning, until that resource exists, and the next initialization applies it. Any other
manifest that fails is reported, and doesn't stop the others.

- ``manage.py initialize_platform`` applies the whole repository, owned by the Smarter admin, so
  that every account may use its resources, and deploys its LLMClients, except in the local
  environment. It does so after ``manage.py initialize_providers``,
  ``manage.py install_official_extensions`` and ``manage.py initialize_vectorstore_providers``,
  whose Providers, Secrets and :doc:`Extensions </smarter-platform/extensions>` the examples use,
  and before the :doc:`Stackademy example project <stackademy>`. The example CustomDomain is applied
  without starting its verification.
- ``manage.py initialize_account`` gives each account its own copy of the example plugins and
  LLMClients, and deploys them, with ``--include_kind``, which applies only the kinds that it
  names. ``--exclude_kind`` does the opposite.
- A Budget whose manifest lists no ``spec.resources`` is created detached, once. If the Budget
  exists, it is left as it is, so the resources that a superuser attached it to, and their changes
  to it, survive the next initialization.
- Applying never deletes anything. A resource whose manifest was removed from the repository stays
  on every platform that loaded it, until ``manage.py delete_retired_examples``, which
  ``manage.py initialize_platform`` runs after the example manifests, deletes it. To retire an
  example, remove its manifest from the repository, and add it to
  :data:`~smarter.apps.account.management.commands.delete_retired_examples.RETIRED_EXAMPLES`.

.. code-block:: console

   python manage.py load_from_github --url https://github.com/smarter-sh/example-manifests --include_kind LLMClient --deploy

See :doc:`/smarter-resources/account/commands/load_from_github` and
:doc:`/smarter-resources/account/commands/initialize_platform`.

Contributing an Example
-----------------------

To change an example, or add one, open a pull request on
`smarter-sh/example-manifests <https://github.com/smarter-sh/example-manifests>`__. Put the manifest
in the folder of its kind, install the repository's pre-commit hooks, and commit: the hooks
validate it against its kind's JSON Schema, as the pull request's checks do. Every platform picks
up the merged change the next time that it is initialized, e.g. on its next deployment.
