Smarter Plugin
===============

Plugins extend LLM tool functionality using Smarter Application Manifests (SAM) instead
of writing and deploying custom Python code. There are three kinds of Smarter Plugin:

 - **Static Plugins**: These plugins provide structured data that is part of the SAM itself.
 - **SQL Plugins**: These plugins allow you to run SQL queries against a connected database.
 - **API Plugins**: These plugins allow you to connect to external APIs.

.. toctree::
   :maxdepth: 1

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
