Smarter Connection
===================

Overview
--------


**Connection Types**

 - :doc:`connection/api`: Connect to REST APIs.
 - :doc:`connection/sql`: Connect to SQL databases.


.. seealso::

    - :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>`
    - :doc:`Smarter Chatbot <../smarter-resources/smarter-chatbot>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter React UI <../smarter-framework/smarter-react-ui>`


Example Manifest
-----------------------

.. literalinclude:: ../../../smarter/smarter/apps/connection/data/sample-connections/smarter-test-db.yaml
    :language: yaml
    :caption: Example SQL Database Connection Manifest

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   connection/resources/api
   connection/resources/sql
   connection/models
   connection/manifests
   connection/serializers
   connection/const
   connection/signals
   connection/receivers
   connection/tasks
   connection/views
