Software Architecture
=====================

**Why Smarter.** Smarter records why it is built the way it is in thirty-one
:doc:`Architecture Decision Records </adr>`, on topics from the choice of Django and Kubernetes to
caching, task queues, API versioning and feature flags. Students can read the reasoning behind a
large system's design, and then check it against the code.

**Look at.** ``docs/source/adr/``, and the broker model that connects manifests to Django models.

**Read.** :doc:`/adr`, :doc:`/smarter-framework/smarter-broker-model`,
:doc:`/smarter-framework/guides/12-factor-app`.

**Exercises.**

- Pick one ADR, find the code that implements it, and judge whether the code still matches the
  decision.
- Argue the opposite of an ADR: what would Smarter look like if it had chosen differently, and
  what would that have cost?
- Draw Smarter's architecture, from the browser and CLI to the database, the workers and the
  model providers, as a C4 container diagram.
- Write an ADR for a design decision in their own project.

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
