Smarter Plugin
===============

Plugins extend LLM tool functionality using :doc:`Smarter Application Manifests (SAM) <../smarter-framework/pydantic/smarter-manifests>` instead
of writing and deploying custom Python code. There are three kinds of Smarter Plugin, two of
which require a ``Connection`` resource as well as a ``Secret`` resource to store authentication
credentials:

**Plugins Types**

 - :doc:`plugins/plugin/static`: These plugins provide structured data that is part of the SAM itself.
 - :doc:`plugins/plugin/sql`: These plugins allow you to run SQL queries against a connected database.
 - :doc:`plugins/plugin/api`: These plugins allow you to connect to external APIs.

**Connection Types**

 - :doc:`plugins/connection/api`: Connect to REST APIs.
 - :doc:`plugins/connection/sql`: Connect to SQL databases.

**Live Demo**

.. raw:: html

   <div style="text-align: center;">
     <video src="https://cdn.smarter.sh/videos/read-the-docs2.mp4"
            autoplay loop muted playsinline
            style="width: 100%; height: auto; display: block; margin: 0; border-radius: 0;">
       Sorry, your browser doesn't support embedded videos.
     </video>
     <div style="font-size: 0.95em; color: #666; margin-top: 0.5em;">
       <em>Smarter Prompt Engineering Workbench Demo</em>
     </div>
   </div>
   <br/>


.. toctree::
   :maxdepth: 1
   :caption: Plugin Technical References

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
