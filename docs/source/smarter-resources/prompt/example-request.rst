Example Prompt Request
======================

Usage
----------------

.. code-block:: bash

  # Deployed Smarter LLMClient
  curl -X POST https://stackademy-sql.3141-5926-5359.api.example.com/prompt/ \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "hello world"}]}'

  # Smarter platform api, by the LLMClient's id
  curl -X POST http://localhost:9357/api/v1/llm-clients/9/prompt/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Token <YOUR-API-KEY>" \
    -d '{"session_key": "<SESSION-KEY>", "messages": [{"role": "user", "content": "hello world"}]}'

.. note::

  There are multiple possible hosts and paths that lead to this endpoint, depending on your
  use case.


.. seealso::

  - :doc:`Example Prompt Config <./example-config>`
  - :doc:`Example Prompt Response <./example-response>`
  - :doc:`Django Hosts <../../smarter-framework/developer-reference/lib/django/hosts>`
  - :doc:`The Chat API Contract <../../smarter-framework/smarter-chat/api-contract>`
  - class reference :py:class:`smarter.apps.prompt.views.PromptWorkbenchView`


Example JSON Object
--------------------

.. literalinclude:: examples/request.json
   :language: json
   :caption: Example request body, sent by the chat UI to the Smarter API
