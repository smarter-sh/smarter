Smarter Connection
===================

Overview
--------


**Connection Types**

 - :doc:`connection/resources/api`: Connect to REST APIs.
 - :doc:`connection/resources/sql`: Connect to SQL databases.


.. seealso::

    - :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>`
    - :doc:`Smarter Chatbot <../smarter-resources/smarter-chatbot>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter Chat <../smarter-framework/develop-reference/react-integration/smarter-chat>`


Example Manifest
-----------------------

.. literalinclude:: ../../../smarter/smarter/apps/connection/data/sample-connections/smarter-test-db.yaml
    :language: yaml
    :caption: Example SQL Database Connection Manifest

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   connection/api
   connection/const
   connection/manifest
   connection/models
   connection/receivers
   connection/resources
   connection/serializers
   connection/signals
   connection/tasks
   connection/templatetags
   connection/urls
   connection/views
