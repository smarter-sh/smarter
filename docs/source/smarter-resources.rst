Smarter Resources
=================

Smarter Resources are a combination of LLM Provider APIs, SQL database data, AWS cloud infrastructure, and Kubernetes resources
that work in concert to provide configurable, secure, scalable and performant AI-powered building blocks for
developers, data scientists and prompt engineers.

Smarter considers the entire lifecycle of an AI resource, from declaration through provisioning, testing,
deployment, scaling, monitoring, maintenance, change management, and sunsetting. Smarter considers the technical
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
