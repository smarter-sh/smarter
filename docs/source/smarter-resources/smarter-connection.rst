Smarter Connection
===================

Overview
--------

A Connection is a Smarter resource type that defines and stores the credentials
and configuration needed to access an external system on which an AI application
depends — most commonly a relational database or a REST API. Like every Smarter resource, a
Connection is declared through a manifest conforming to the Smarter Application
Manifest (SAM) specification, with apiVersion, kind, metadata, and spec sections.
The spec captures the connection details required to establish a session with the
target system: engine/driver, network location, authentication credentials, and
pooling or timeout behavior, depending on the connection type. Once applied, a
Connection exists as a named, reusable resource that other resources in the
platform — such as Plugins or data-driven applications — can reference by name
to read from or write to that backend, without needing to redeclare connection
details in every dependent resource.

Connections exist to separate how to reach a system from what to do with it once
connected. This separation keeps credentials centralized and governed in one place,
allows a single underlying system to be shared across multiple applications or
environments through a simple name reference, and lets connection details change
independently of the resources that depend on them. Because a Connection is a
first-class SAM resource, it follows the same lifecycle as every other resource
type in the platform — apply, get, describe, delete — so database and service
connectivity can be managed declaratively, version-controlled, and audited
alongside the rest of an AI application's configuration, rather than handled
as out-of-band infrastructure setup.

**Connection Types**

 - :doc:`connection/resources/api`: Connect to REST APIs.
 - :doc:`connection/resources/sql`: Connect to SQL databases.


.. seealso::

    - :doc:`Smarter API Manifest (SAM) <../smarter-framework/smarter-api>`
    - :doc:`Smarter LLMClient <../smarter-resources/smarter-llmclient>`
    - :doc:`Smarter CLI <../smarter-framework/smarter-cli>`
    - :doc:`Smarter Chat <../smarter-framework/developer-reference/react-integration/smarter-chat>`


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
