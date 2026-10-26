Smarter Python SDK
==================

The Smarter Python SDK is the official Python library of the :doc:`Smarter API <smarter-api>`. It is
to Smarter what the ``openai`` package is to the OpenAI API: one ``pip install`` gives your Python
software typed, complete access to your own Smarter platform, whether it runs on your laptop or on
:doc:`Kubernetes <smarter-on-kubernetes>`. It covers every resource kind through the same
:doc:`manifest API <smarter-api/cli>` as the :doc:`Smarter CLI <smarter-cli>`, prompts and streamed
chats with :doc:`LLMClients <../smarter-resources/smarter-llmclient>`, each resource's own actions,
and typed Pydantic models of every :doc:`manifest <smarter-manifests>` kind and of the platform's
API contracts.

.. code-block:: console

   pip install smarter-api

.. code-block:: python

   from smarter import Smarter

   client = Smarter()  # SMARTER_API_KEY, or the smarter cli's ~/.smarter/config.yaml

   llmclient = client.llm_clients.find("customer_support")
   print(client.llm_clients.prompt(llmclient.id, "Where is my order #1234?").text)

The SDK has its own documentation site, with its user guide, API reference and architecture
decisions: `docs.smarter-python.smarter.sh <https://docs.smarter-python.smarter.sh/>`__.

The package is ``smarter-api`` on `PyPI <https://pypi.org/project/smarter-api/>`__, and its import
name is ``smarter``. Its source is
`github.com/smarter-sh/smarter-python <https://github.com/smarter-sh/smarter-python>`__. It takes
the list of manifest kinds and the journal's enumerations from the same package as the platform,
:doc:`smarter-types <developer-reference/smarter-types>`, so the two always agree.
