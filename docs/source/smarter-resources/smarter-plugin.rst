Smarter Plugin
===============

Plugins extend LLM tool functionality using Smarter Application Manifests (SAM) instead
of writing and deploying custom Python code. There are three kinds of Smarter Plugin:

**Plugins Types**

 - :doc:`plugins/plugin/static`: These plugins provide structured data that is part of the SAM itself.
 - :doc:`plugins/plugin/sql`: These plugins allow you to run SQL queries against a connected database.
 - :doc:`plugins/plugin/api`: These plugins allow you to connect to external APIs.

**Connection Types**

 - :doc:`plugins/connection/api`: Connect to REST APIs.
 - :doc:`plugins/connection/sql`: Connect to SQL databases.

.. toctree::
   :maxdepth: 1

   plugins/resource-types
   plugins/how-it-works
   plugins/how-tools-work
   plugins/api
   plugins/models
   plugins/manifests
   plugins/serializers
   plugins/const
   plugins/nlp
   plugins/signals
   plugins/plugin
   plugins/tasks
   plugins/utils
   plugins/views
