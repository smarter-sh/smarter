Smarter AI Resource Reference
==============================

Smarter is a governed platform for building LLM-powered applications. Every capability in Smarter —
from calling a model, to running a tool, to storing a credential — is expressed as a declarative
**Resource**. Resources compose into four layers, and understanding those layers is the fastest way
to understand the platform:

**Access & Governance**
   :doc:`smarter-resources/smarter-account` and :doc:`smarter-resources/smarter-secret` establish who
   is acting, what they're permitted to access and spend, and how credentials are stored and retrieved without
   ever appearing in plaintext. Every other resource operates within the boundaries these two sets.

**Model Connectivity**
   :doc:`smarter-resources/smarter-provider` and :doc:`smarter-resources/smarter-llmhost` are the two
   ways a model reaches Smarter — a third-party API such as OpenAI or Anthropic, or a self-hosted,
   freely downloadable model you run and manage yourself. :doc:`smarter-resources/smarter-llm_client`
   sits in front of both, giving prompts and applications one consistent interface regardless of which
   kind of model is actually answering the request.

**Extensibility & Trust**
   :doc:`smarter-resources/smarter-plugin` is how a model does things beyond generating text — Static,
   Skill, API, and SQL tool calls — reaching external systems through
   :doc:`smarter-resources/smarter-connection` and the wider Model Context Protocol ecosystem through
   :doc:`smarter-resources/smarter-mcpclient`. :doc:`smarter-resources/smarter-vectorstore` gives those
   plugins and prompts a self-hosted knowledge base to retrieve from. None of this is unsupervised:
   :doc:`smarter-resources/smarter-guardrail` inspects every request and response, enforcing moderation
   and security policy regardless of which model, plugin, or data source is involved.

**Conversation**
   :doc:`smarter-resources/smarter-prompt` is where it all lands — a chat conversation with archivable
   history, capturing what was asked, what tools ran, what the guardrails did, and what came back.

This layered design is what makes Smarter auditable end to end: an administrator can trace any single
:doc:`smarter-resources/smarter-prompt` back through the guardrail checks, tool calls, and model
connection that produced it, and back further still to the account and budget that authorized it in
the first place.

Every Resource is declared using a :doc:`Smarter Application Manifest (SAM) <../smarter-framework/smarter-manifests>`,
a `YAML <https://en.wikipedia.org/wiki/YAML>`__ file that defines its desired state. This declarative
approach means Resources can be versioned, diffed, and reviewed like any other infrastructure-as-code —
and because SAM files are plain, human-readable YAML, they can be understood by non-developers, like
business analysts and product managers, not just by the engineers who apply them.

.. literalinclude:: ../../smarter/smarter/apps/account/data/example-manifests/secret-smarter-test-db.yaml
  :language: yaml
  :caption: Example Manifest


Smarter manifest files are processed by the :doc:`Smarter CLI <smarter-framework/smarter-cli>`, which interacts seamlessly and securely
with the :doc:`Smarter API <smarter-framework/smarter-api>` to provision, update, and manage the lifecycle of Smarter Resources.
The Smarter Project maintains a :doc:`VS Code Extension <smarter-framework/vs-code-extension>` that provides syntax highlighting,
manifest validation, and inline documentation for authoring SAM files.

Because Resources are layered rather than monolithic, different roles on a team naturally gravitate
toward different parts of the stack, without needing to understand the whole thing to be productive:

- **Prompt engineers** work in the Conversation and Extensibility layers — :doc:`smarter-resources/smarter-prompt`, :doc:`smarter-resources/smarter-plugin`, and :doc:`smarter-resources/smarter-guardrail` — using :doc:`YAML manifests <../smarter-framework/smarter-manifests>` and the :doc:`Smarter CLI <smarter-framework/smarter-cli>`.
- **Business Process Analysts** work downstream of the Conversation layer, querying archived :doc:`smarter-resources/smarter-prompt` history and :doc:`smarter-resources/smarter-account` usage data through Smarter's MySQL database and reporting tools.
- **Application developers** work in the Extensibility layer, wiring :doc:`smarter-resources/smarter-connection` and :doc:`smarter-resources/smarter-mcpclient` resources into applications using Python, the :doc:`Smarter Application Framework <../smarter-framework>`, and its built-in :doc:`REST APIs <../smarter-framework/smarter-api>`.
- **Data scientists** work in the Model Connectivity layer, deploying and evaluating models and retrieval pipelines through :doc:`smarter-resources/smarter-llmhost` and :doc:`smarter-resources/smarter-vectorstore`.
- **DevOps engineers** work in the Access & Governance layer, provisioning :doc:`smarter-resources/smarter-secret` and :doc:`smarter-resources/smarter-llmhost` infrastructure through the :doc:`Smarter CLI <../smarter-platform/cli>`, :doc:`GitHub Actions <../smarter-framework/developer-reference/devops/ci-cd>`, and `Kubernetes <https://artifacthub.io/packages/helm/project-smarter/smarter>`_.
- **Cloud engineers** work alongside DevOps in Access & Governance and Model Connectivity, using Smarter's :doc:`AWS <../smarter-framework/technologies/aws>` and :doc:`Kubernetes <../smarter-framework/technologies/kubernetes>` Helper classes to scale self-hosted infrastructure.


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-resources/smarter-account
   smarter-resources/smarter-connection
   smarter-resources/smarter-guardrail
   smarter-resources/smarter-llm_client
   smarter-resources/smarter-llmhost
   smarter-resources/smarter-mcpclient
   smarter-resources/smarter-plugin
   smarter-resources/smarter-prompt
   smarter-resources/smarter-provider
   smarter-resources/smarter-secret
   smarter-resources/smarter-vectorstore
