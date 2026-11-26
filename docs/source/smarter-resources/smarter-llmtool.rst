Smarter LLMTool Plugin
======================

Overview
--------

LLMTool Plugins ("plugins") provide a `declarative <https://en.wikipedia.org/wiki/Declarative_programming>`__
`yaml <https://en.wikipedia.org/wiki/YAML>`__
`manifest <https://kubernetes.io/docs/concepts/overview/working-with-objects/>`__
alternative to programming in Python in order to
extend :doc:`LLM tool functionality <llmtool/how-tools-work>`. Every kind of Smarter plugin extends the LLM
tool specification, so in these docs "plugin" always means a Smarter LLMTool Plugin. Plugins are
implemented in the ``smarter.apps.llmtool`` Django app.

.. important::

   Smarter's plugins protect your AI application from bad actors in several ways: they run their calls
   in a special, isolated sandbox that can't reach Smarter's internal resources on its private network;
   they receive only the credentials that each
   call needs for its own information retrieval; and they run only verified code, from the platform's
   own dependencies to every extension (see **Plugin Execution Sandbox**, below).

:doc:`Smarter Application Manifests (SAM) <../smarter-framework/developer-reference/lib/drf/manifest>`
are used to :doc:`define LLMTool Plugins <llmtool/how-it-works>`, which can be used to provide several powerful kinds of
enterprise data integrations, two of which require a ``Connection`` resource as well as a ``Secret``
resource to store authentication credentials:

**Plugin Types**

 - :doc:`llmtool/plugin/skill`: These plugins provide Anthropic standard Skills definitions in markdown format. See `The Complete Guide To Building Skills For Claude <https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf>`__
 - :doc:`llmtool/plugin/websearch`: Experimental. These plugins search the open web, and read web pages, with citations.
 - :doc:`llmtool/plugin/image-search`: Experimental. These plugins search for images with the Brave Image Search API, and return a list of image urls.
 - :doc:`llmtool/plugin/static`: These plugins provide structured data that is part of the SAM itself.
 - :doc:`llmtool/plugin/sql`: These plugins allow you to run SQL queries against a connected database.
 - :doc:`llmtool/plugin/api`: These plugins allow you to connect to external APIs.

**Connection Types**

 - :doc:`connection/resources/api`: Connect to REST APIs.
 - :doc:`connection/resources/sql`: Connect to SQL databases.

**Plugin Execution Sandbox**

As with WordPress, plugins increase an AI application's attack surface. In Smarter, a plugin designed to
access an external resource like a database, an API or to search the web runs its calls inside a
special sandboxed environment: Smarter's
:doc:`tool worker <../smarter-framework/smarter-on-kubernetes/tool-worker>`, a standalone Kubernetes
pod whose capabilities are restricted in several ways.

 - **Credentials.** The sandbox lacks access to sensitive environment data that normal pods have.
   By contrast, it receives exactly one credential at a time: the credential for the external resource that the plugin
   is trying to reach, and only for the duration
   of the call that it is running. Meanwhile, it does **not** have access to Smarter's database password,
   nor its Secrets, its
   encryption key, its LLM provider keys, nor any kind of cloud role nor a Kubernetes token. It is
   effectively unable to interact with the Django framework in any way.
 - **Infrastructure.** The sandbox's root filesystem is completely read-only and it runs as a non-root
   user: it can write only to temporary
   scratch volumes, which are erased with the pod. So malicious code can't modify Smarter's own code
   nor its third-party PyPi Python packages, it can't download nor plant a backdoor that would survive a restart,
   and it can't install tools
   nor gain root access to break out of the container. Anything it does write disappears with the pod.
 - **Network.** The sandbox's pods run in an application group of their own, ``smarter-tools``.
   Other kinds of Smarter pods can communicate with each other. But not these, these are isolated.
   They are also subject to stricter network policies:

   - **Outbound to the internet:** they can reach public addresses, on ports 443, 80 and 3306,
     but not private ones. *(Keep in mind that reaching APIs,
     databases and web sites that a manifest author or the LLM chooses is the sandbox's sole job.)*
   - **Outbound from inside the platform:** these pods can communicate with only three services:

     - Redis, which acts as a broker by delivering tool calls to the sandbox and carrying their results back to the platform.
     - DNS, to look up host names.
     - Smarter's own MariaDB server, though only in isolated cases for Smarter's example plugins for its tutorials. [#mariadb]_

   - **No private addresses:** the sandbox can't reach any private nor link-local address: not
     the app's pods, nor the other pod workers, the cluster's nodes, the Kubernetes API nor the cloud's
     instance metadata service. Likewise, its HTTP client refuses private addresses too, on every request and
     every redirect, so a url that resolves to one fails before the network policy is even needed.
   - **Inbound:** nothing. No pod, inside or outside the cluster, can open a connection to the
     sandbox.
 - **Code execution.** The sandbox runs as a non-root user, with every Linux capability stripped
   away. No file system privilege escalation is possible. A seccomp filter also blocks the dangerous calls
   that a program can make to the Linux kernel, such as loading kernel modules or rebooting the
   machine, which are the usual ways out of a container. It runs only the
   platform's own code, and extensions from the signed extension registry, whose code it checks
   against its sha256 before loading it. Lastly, every call is subject to a short timeout.

See :doc:`../smarter-platform/system-administration/security/application`.

.. [#mariadb] For SQL plugins whose database is hosted on the same server as Smarter's, such as
   Stackademy's. However, the sandbox is strictly **unable** to access Smarter's own application database.

Plugins are fundamentally more feature rich than traditional :doc:`LLM function tools <llmtool/how-tools-work>`. An LLMTool Plugin manifest
defines not only what proprietary data is being made available to the LLM, but also the LLM prompt specification itself
(which provider, model, temperature, etc.), and most importantly, the criteria which
the tool should be presented to the LLM.

.. important::

  Imagine a use case in which you have hundreds or
  thousands of tools. It would be impractical (and exceedlingly expensive) to present all of those tools
  to the LLM for every prompt. Instead, LLMTool Plugins allow you to define:

  - **Selector**: CSS-like logic that defines when the tool should be made available to the LLM. That is, when it
    should be included in the prompt as an available tool. Remember that LLM APIs charge by token, and including
    tools in a prompt request increases the token count. Therefore, it behooves one to be judicious about which tools
    are made available to the LLM for any given prompt.
  - **Prompt**: The prompt specification that defines which LLM provider, the model, temperature, and other
    parameters to use when invoking the tool. You can even modify, or completely redefine the system prompt used
    when invoking the tool.
  - **Data**: The structured data that is made available to the LLM when the tool is invoked. This
    is further defined by the plugin type (static data, SQL, or API). In the example below of a Static Plugin, the first level
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

.. seealso::

    - :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>`
    - :doc:`Smarter LLMClient <../smarter-resources/smarter-llmclient>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter Chat <../smarter-framework/smarter-chat>`

Usage
-----

.. code-block:: yaml

  apiVersion: smarter.sh/v1
  kind: LLMClient
  metadata:
    name: stackademy_sql
    description: Stackademy University course catalogue inquiries using the Stackademy SQL plugin.
    version: 1.0.0
  spec:
    config:
      prompt:
        provider: openai
        defaultModel: gpt-4-turbo
        defaultSystemRole: You are a helpful assistant.
    plugins:
      - stackademy_sql

Example Manifest
-----------------------

.. code-block:: yaml
   :caption: Example SQL Plugin Manifest

   apiVersion: smarter.sh/v1
   kind: SqlPlugin
   metadata:
     description: Online course catalogue inquiries for fictional Stackademy University that only offers computer science degrees programs.
     name: stackademy_sql
     pluginClass: sql
     version: 0.1.0
     tags:
       - db
       - sql
       - database
     annotations:
       - smarter.sh/stackademy-sql/display-name: Stackademy SQL
       - smarter.sh/stackademy-sql/icon: https://example.com/stackademy-sql-icon.png
       - smarter.sh/stackademy-sql/documentation-url: https://docs.stackademy.com/sql
       - smarter.sh/stackademy-sql/contact-email: no-reply@example.com
   spec:
     selector:
       directive: always
     prompt:
       provider: openai
       systemRole: >
         You are a helpful student advisor at the fictional Stackademy University that only offers computer science
         degrees programs. Whenever possible you should defer to the tool calls provided for additional information
         about the courses offered by Stackademy University. Questions unrelated to the courses or Stackademy University
         should be answered with "I am sorry, but I can only provide information about the courses offered by Stackademy University."
       model: gpt-6-luna
       temperature: 1.0
       maxTokens: 2048
     connection: stackademy_catalog_db
     sqlData:
       limit: 10
       sqlQuery: SELECT c.course_code, c.course_name, c.description, c.cost, prerequisite.course_code AS prerequisite_course_code, prerequisite.course_name AS prerequisite_course_name
         FROM courses c
         LEFT JOIN courses prerequisite ON c.prerequisite_id = prerequisite.course_id
         WHERE ((c.description LIKE CONCAT('%', {description}, '%')) OR ({description} IS NULL))
           AND (c.cost <= {max_cost} OR {max_cost} IS NULL)
         ORDER BY c.prerequisite_id;
       parameters:
       - description: the maximum cost that a student is willing to pay for a course.
         enum: null
         name: max_cost
         required: false
         type: number
       - description: areas of specialization for courses in the catalogue.
         enum:
         - AI
         - mobile
         - web
         - database
         - network
         - neural networks
         name: description
         required: false
         type: string
       testValues:
       - name: description
         value: AI
       - name: max_cost
         value: 500

From `plugins/sql/stackademy-sql.yaml <https://github.com/smarter-sh/stackademy/blob/main/plugins/sql/stackademy-sql.yaml>`__ in the :doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   llmtool/api
   llmtool/caching
   llmtool/const
   llmtool/how-it-works
   llmtool/how-tools-work
   llmtool/resource-types
   llmtool/management
   llmtool/models
   llmtool/manifests
   llmtool/serializers
   llmtool/nlp
   llmtool/signals
   llmtool/receivers
   llmtool/runner
   llmtool/tasks
   llmtool/views
