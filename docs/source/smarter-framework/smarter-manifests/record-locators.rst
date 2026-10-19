Record Locators and Dependency Trees
====================================

Every Smarter resource has a record locator, which a manifest returns as ``status.recordLocator``: the
lower-cased name of the resource's Django model, a hyphen, and the row's hashed id, e.g.
``llmclient-rMTAwMDAxMwx`` or ``pluginmeta-rMTAwMDAyMwx``. The web console addresses a resource's page by the
same hashed id, so a record locator is enough to build the url of that page, without a database query.

A broker's ``dependency_tree()`` uses this to describe a resource and, recursively, every resource that it
uses, each by its record locator and with the path of its web console page, so that a console page can draw
the tree with a link on each resource. Each kind of resource says what it uses in its broker's
``references()``, the opposite of ``dependents()``, which says what depends on it and keeps a resource that
is still in use from being deleted.

.. code-block:: python

    from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker

    broker = SAMLLMClientBroker(None, name="stackademy_sql", kind="LLMClient", user_profile=user_profile)
    print(broker.dependency_tree().model_dump_json(indent=2))

.. code-block:: text

    LLMClient stackademy_sql            /workbench/llm-clients/rMTAwMDAyMgx/prompt/
    ├── Provider openai                 /provider/providers/rMTAwMDAwNwx/
    │   └── Secret openai_api_key       /secret/secrets/rMTAwMDAxMQx/
    └── SqlPlugin stackademy_sql        /llm-tools/plugins/rMTAwMDAyMwx/
        ├── Provider openai             /provider/providers/rMTAwMDAwNwx/
        │   └── Secret openai_api_key   /secret/secrets/rMTAwMDAxMQx/
        └── SqlConnection smarter_test_db   /connection/connections/sql-connection/rMTAwMDAwMQx/
            └── Secret smarter_test_user    /secret/secrets/rMTAwMDAxNQx/

A resource that two others use appears under each of them. A resource that the user may not read keeps its
kind and record locator, but not its name, its url, or what it uses in turn.

.. automodule:: smarter.lib.manifest.record_locator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: smarter.lib.manifest.models.SAMDependencyTreeNode
   :members:
   :no-index:
