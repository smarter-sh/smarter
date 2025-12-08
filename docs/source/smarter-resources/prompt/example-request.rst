Example Prompt Request
======================

Usage
----------------

.. code-block:: bash

  # Smarter Prompt Engineer Workbench
  curl -X POST http://localhost:8000/api/v1/chatbots/9/chat/?session_key=e5c0368d6d7201b60f4f20c470f4b5ba36faf45e80ddbe8b04b6cf20f33167a7

  # Deployed Smarter Chatbot - Alpha
  curl -X GET https://stackademy.3141-5926-5359.alpha.api.example.com/chat/?session_key=<SESSION-KEY>

  # Deployed Smarter Chatbot - Production
  curl -X GET https://stackademy.3141-5926-5359.api.example.com/chat/?session_key=<SESSION-KEY>

.. note::

  There are multiple possible hosts and paths that lead to this endpoint, depending on your
  use case.


.. seealso::

  - :doc:`Example Prompt Config <./example-config>`
  - :doc:`Example Prompt Response <./example-response>`
  - :doc:`Django Hosts <../../smarter-framework/django/hosts>`
  - :doc:`Smarter React UI <../../smarter-framework/smarter-react-ui>`
  - class reference :py:class:`smarter.apps.prompt.views.ChatAppWorkbenchView`


Example JSON Object
--------------------

.. literalinclude:: ../../../../smarter/smarter/apps/prompt/data/request.json
