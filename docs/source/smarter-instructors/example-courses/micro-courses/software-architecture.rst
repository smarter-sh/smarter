Software Architecture
=====================

**Why Smarter.** Architecture is usually taught with boxes and arrows drawn for systems that
students can never open. Smarter is the opposite: a large, production system whose reasons are
written down and whose code is public. It records why it is built the way it is in thirty-one
:doc:`Architecture Decision Records </adr>`, from :doc:`the choice of Django </adr/001-django>`
and :doc:`Kubernetes </adr/003-kubernetes>` to :doc:`caching </adr/018-caching>`,
:doc:`task queues </adr/030-task-queues>`, :doc:`API versioning </adr/023-api-versioning>` and
:doc:`Pydantic contracts </adr/031-pydantic-over-json>`. Students can read the reasoning behind
each decision, then open the code and judge whether the two still agree.

Smarter also follows, in code that students can read, the principles that working architects use
as a shared vocabulary. :doc:`ADR 004 </adr/004-12-factor>` makes
`The Twelve-Factor App <https://12factor.net/>`__ binding on every pull request, and each factor
has a concrete home: a `settings module per environment
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/settings>`__, configuration
validated by a `Pydantic Settings class
<https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf/settings.py>`__, one
`multi-stage Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__ for every
process type, sessions kept in Redis, and liveness and readiness probes in the
`Helm chart <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter/templates>`__.
Beyond the twelve factors, students find:

- **Classic patterns.** Django's Model-View-Template, its version of Model-View-Controller, in
  every resource family: a `model
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/models.py>`__,
  `URL patterns <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/secret/urls.py>`__,
  views and `templates <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/templates>`__,
  with MVC split between Django and a React app on the web console's pages. Underneath runs a
  descendant of the LAMP stack: Linux, MariaDB and Python, with uvicorn in Apache's place.
- **Ports and adapters.** All DNS, certificate, Kubernetes and email work goes through one
  `infrastructure facade
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/services/__init__.py>`__,
  with an AWS provider in production and an `in-memory provider
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/infrastructure/providers/memory.py>`__
  in tests.
- **Extensibility.** A :doc:`broker model </smarter-framework/smarter-broker-model>` with a
  `registry of resource kinds
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/cli/brokers.py>`__,
  a `PluginBase <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/plugin/plugin/base.py>`__
  class for new plugin types, and :doc:`new LLM providers added by manifest
  </smarter-platform/adding-an-llm-provider>`, not code.
- **Explicit data models.** Django models for what is stored, Pydantic models for what crosses a
  boundary, and an `ownership base class
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/account/models/metadata_with_ownership.py>`__
  that makes every resource belong to an account.
- **Infrastructure as code.** Terraform and Terragrunt in
  `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__, a Helm chart
  validated by a `JSON schema
  <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.schema.json>`__, and
  Smarter itself as a declarative system that turns YAML manifests into database rows, DNS
  records and Kubernetes ingresses.
- **Zero trust.** Hashed API keys checked on every call, querysets filtered by owner, secrets
  encrypted at rest, `network policies
  <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__
  between pods, outbound plugin calls that `refuse private addresses
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/plugin/plugin/safe_http.py>`__,
  and the model itself treated as untrusted, with :doc:`guardrails
  </smarter-resources/smarter-guardrail>` on its input and output.

The system is big enough for these decisions to matter (more than five thousand unit tests, and
eighteen Django apps), and small enough for a student to hold the whole of it in their head by the
end of the course.

**What the course covers.** What architecture is, and the quality attributes that drive it;
quality attribute scenarios; describing a system with the C4 model; reading, verifying and writing
ADRs; the twelve factors, one by one, against the code; a review of the classic patterns,
Model-View-Controller, Model-View-Template and the LAMP stack; styles and patterns, from modular
monolith to ports and adapters; horizontal scalability, caching and task queues; data models and contracts;
infrastructure as code; zero trust and the architecture of AI applications; and how an
architecture evolves, including when coding agents write much of the code.

**Look at.**

- `docs/source/adr/ <https://github.com/smarter-sh/smarter/tree/main/docs/source/adr>`__, the
  decision records themselves.
- `smarter/smarter/apps/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps>`__,
  one Django app per resource family, and
  `smarter/smarter/lib/manifest/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/manifest>`__,
  the broker and manifest framework that connects them.
- `docker-compose.yml <https://github.com/smarter-sh/smarter/blob/main/docker-compose.yml>`__ and
  `helm/charts/smarter/templates/ <https://github.com/smarter-sh/smarter/tree/main/helm/charts/smarter/templates>`__,
  the same containers locally and on Kubernetes.
- `smarter/smarter/apps/infrastructure/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/infrastructure>`__,
  the ports-and-adapters service layer.

Each course plan lists every file that it uses, factor by factor and principle by principle, under
*Principles in the Source Code*.

**Read.** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
:doc:`/smarter-framework/guides/12-factor-app`, :doc:`/smarter-platform/cloud-infrastructure`,
:doc:`/smarter-platform/security`.

**Exercises.**

- Pick one ADR, find the code that implements it, and judge whether the code still matches the
  decision.
- Audit four of the twelve factors against the code, with file and line references, and combine
  the class's findings into a scorecard for the whole system.
- Trace one request to the web console, from the URLconf through the view and template to the
  React app and the JSON API it calls, and label each part as model, view or controller.
- Argue the opposite of an ADR: what would Smarter look like if it had chosen differently, and
  what would that have cost?
- Draw Smarter's architecture, from the browser and CLI to the database, the workers and the
  model providers, as a C4 container diagram, from ``docker-compose.yml`` and the Helm templates.
- Write an ADR for a design decision in their own project.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <software-architecture/bootcamp>
   Two-week online course: 6 hours <software-architecture/two-week>
   Four-week online course: 12 hours <software-architecture/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
