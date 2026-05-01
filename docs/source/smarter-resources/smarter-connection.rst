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
    - :doc:`Smarter React UI <../smarter-framework/react-integration/smarter-chat>`


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
   connection/models
   connection/serializers
   connection/const
   connection/receivers
   connection/resources
   connection/signals
   connection/sam
   connection/tasks
   connection/views
