Smarter Resources
=================

Smarter Resources are a combination of :doc:`LLM Provider APIs <smarter-resources/smarter-provider>`, :doc:`SQL database data <smarter-framework/django>`,
:doc:`AWS cloud infrastructure <smarter-framework/aws>`, and :doc:`Kubernetes resources <smarter-framework/kubernetes>`
that work in concert to provide configurable, secure, scalable and performant AI-powered building blocks for
developers, data scientists and prompt engineers.

Smarter Resources are declared using :doc:`Smarter Application Manifests (SAM) <smarter-framework/pydantic/smarter-manifests>`, which are `YAML <https://en.wikipedia.org/wiki/YAML>`__ files
that define the desired state of each resource. Smarter's declarative approach allows for easy versioning, change management, and collaboration among team members.
And importantly, SAM files are human-readable, infrastructure-as-code documents that can be reviewed and understood by non-developers,
like business analysts and product managers.

.. literalinclude:: ../../smarter/smarter/apps/account/data/sample-secrets/smarter-test-db.yaml
  :language: yaml
  :caption: Example Manifest


Smarter manifest files are processed by the :doc:`Smarter CLI <smarter-framework/smarter-cli>`, which interacts seamlessly and securely
with the :doc:`Smarter API <smarter-framework/smarter-api>` to provision, update, and manage the lifecycle of Smarter Resources.
The Smarter Project maintains a :doc:`VS Code Extension <smarter-framework/vs-code-extension>` that provides syntax highlighting,


Smarter considers the entire lifecycle of an AI resource, from declaration through provisioning, testing,
deployment, scaling, monitoring, maintenance, change management, and its eventual sunsetting. Smarter considers the technical
capabilities of the various team member roles, and provides usable tools and abstractions for each.

- Prompt engineers work with Smarter  :doc:`YAML manifests <smarter-framework/pydantic/smarter-manifests>` and the :doc:`Smarter CLI <smarter-platform/cli>`.
- Business Process Analysts work with Smarter's MySQL database and reporting tools.
- Application developers work with Python and the :doc:`Smarter Application Framework <smarter-framework>`, and it's built-in :doc:`REST APIs <smarter-framework/smarter-api>`.
- Data scientists work with Python
- DevOps engineers work with :doc:`Smarter CLI <smarter-platform/cli>`, :doc:`GitHub Actions <smarter-framework/devops/ci-cd>`, and `Kubernetes <https://artifacthub.io/packages/helm/project-smarter/smarter>`_.
- Cloud engineers work with Smarter's :doc:`AWS <smarter-framework/aws>` and :doc:`Kubernetes <smarter-framework/kubernetes>` Helpers classes.


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-resources/smarter-account
   smarter-resources/smarter-chatbot
   smarter-resources/smarter-provider
   smarter-resources/smarter-plugin
   smarter-resources/smarter-prompt
