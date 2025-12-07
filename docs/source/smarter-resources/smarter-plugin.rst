Smarter Plugin
===============

Plugins provide a `declarative <https://en.wikipedia.org/wiki/Declarative_programming>`__ `yaml <https://en.wikipedia.org/wiki/YAML>`__ `manifest <https://kubernetes.io/docs/concepts/overview/working-with-objects/>`__ alternative to programming in Python in order to
extend :doc:`LLM tool functionality <plugins/how-tools-work>`. :doc:`Smarter Application Manifests (SAM) <../smarter-framework/pydantic/smarter-manifests>`
are used to :doc:`define Smarter Plugins <plugins/how-it-works>`, which can be used to provide three powerful kinds of
enterprise data integrations, two of which require a ``Connection`` resource as well as a ``Secret``
resource to store authentication credentials:

**Plugins Types**

 - :doc:`plugins/plugin/static`: These plugins provide structured data that is part of the SAM itself.
 - :doc:`plugins/plugin/sql`: These plugins allow you to run docs/build/html/adr.htmlSQL queries against a connected database.
 - :doc:`plugins/plugin/api`: These plugins allow you to connect to external APIs.

**Connection Types**

 - :doc:`plugins/connection/api`: Connect to REST APIs.
 - :doc:`plugins/connection/sql`: Connect to SQL databases.

Plugins are fundamentally more feature rich than traditional :doc:`LLM function tools <plugins/how-tools-work>`. A Smarter Plugin manifest
defines not only what proprietary data is being made available to the LLM, but also the LLM prompt specification itself
(which provider, model, temperature, etc.), and most importantly, the criteria which
the tool should be presented to the LLM.

.. important::

  Imagine a use case in which you have hundreds or
  thousands of tools. It would be impractical (and exceedlingly expensive) to present all of those tools
  to the LLM for every prompt. Instead, Smarter Plugins allow you to define:

  - **Selector**: CSS-like logic that defines when the tool should be made available to the LLM. That is, when it
    should be included in the prompt as an available tool. Remember that LLM APIs charge by token, and including
    tools in a prompt request increases the token count. Therefore, it behooves one to be judicious about which tools
    are made available to the LLM for any given prompt.
  - **Prompt**: The prompt specification that defines which LLM provider, the model, temperature, and other
    parameters to use when invoking the tool. You can even modify, or completely redefine the system prompt used
    when invoking the tool.
  - **Data**: The structured data that is made available to the LLM when the tool is invoked. This
    if further defined by the Plugin type (static data, SQL, or API). In the example below of a Static Plugin, the first level
    of data keys defines the enumerations list that is presented to the tool. In the example below, the keys translate to: 'platform provider', 'about', and 'links'.


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

.. literalinclude:: ../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-sql.yaml
    :language: yaml
    :caption: Example SQL Plugin Manifest
