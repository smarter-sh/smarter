.. _opentelemetry_compatibility:

OpenTelemetry Compatibility
============================

.. note::

   **Status: Proposed / Not yet implemented.**

   This page describes an early design specification for adding
   `OpenTelemetry <https://opentelemetry.io/>`__ (OTel) compatibility to Smarter v0.16. Nothing
   described below has shipped yet, and the design is still open for debate. Please
   join the conversation, ask questions, or propose alternatives in the GitHub
   Discussion below rather than treating this page as a finished spec.

   `Add OpenTelemetry Support - smarter-sh/smarter Discussion #722
   <https://github.com/smarter-sh/smarter/discussions/722>`_

Overview
--------

Smarter orchestrates the full lifecycle of an LLM request: prompt rendering,
guardrails, provider calls, and tool/function execution. Today, that lifecycle is
observable only through application logs. This proposal describes what it would take
to make Smarter's request lifecycle observable via `OpenTelemetry
<https://opentelemetry.io/docs/what-is-opentelemetry/>`_, the CNCF vendor-neutral
standard for traces, metrics, and logs, so that Smarter deployments can plug into
existing observability stacks (Grafana Tempo, Honeycomb, Datadog, Jaeger, and others)
without Smarter having to adopt any single vendor's SDK.

Motivation
----------

Most modern agent frameworks are responsible for more than just calling an LLM SDK.
An LLM SDK (the ``openai``, ``anthropic``, or Google GenAI packages) exposes the raw
tool-calling capability of a model. An agent framework -- which is what Smarter is --
sits a layer above that and orchestrates the entire tool-calling lifecycle:
validating tool names and arguments, executing tools, capturing exceptions, enforcing
permissions, retrying on failure, and feeding results back to the model. That
lifecycle typically looks like this:

.. code-block:: text

   User
    |
    v
   LLM  ---- decides to call a tool
    |
    v
   Agent framework
    |---- validate tool name
    |---- validate arguments
    |---- execute tool
    |---- capture exceptions
    |---- log execution
    |---- enforce permissions
    |---- retry if needed
    |---- return tool result
    |
    v
   LLM
    |
    v
   Final response

Every one of those steps is a candidate for a trace span. Right now none of them are
emitted anywhere that a standard observability backend can consume. Adding
OpenTelemetry compatibility means instrumenting this lifecycle so that it produces
standard traces, using the industry's emerging semantic conventions for generative AI
rather than a bespoke, Smarter-only schema.

What "OpenTelemetry Compatible" means for Smarter
--------------------------------------------------

Being "OpenTelemetry compatible" does **not** mean adopting a specific observability
vendor. It means:

* Smarter emits traces (and eventually metrics) using the `OpenTelemetry Python SDK
  <https://opentelemetry-python.readthedocs.io/en/latest/>`_.
* Span names and attributes follow, wherever applicable, the `OpenTelemetry semantic
  conventions for Generative AI systems
  <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md>`_
  (the ``gen_ai.*`` attribute namespace -- request/response model, token usage,
  operation name, finish reason, and so on).
* Standard HTTP and database spans are produced automatically via existing,
  off-the-shelf instrumentation rather than hand-rolled.
* Trace export is configurable via the standard `OTLP exporter
  <https://opentelemetry.io/docs/specs/otlp/>`_, so operators can point Smarter at
  whatever backend they already run, with no Smarter-specific exporter code to
  maintain.

Proposed architecture
----------------------

Django Signals as the internal event bus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter's Python/Django codebase and the REST API it exposes are the sole
implementations of the platform, so the instrumentation points are all internal to
this codebase. The proposal is to treat each lifecycle step above as a `Django Signal
<https://docs.djangoproject.com/en/stable/topics/signals/>`_, fired by the existing
``LLMClient``, ``Guardrail``, ``Prompt``, ``Provider``, and ``Tool`` classes. This
keeps the instrumentation decoupled from the OTel SDK itself -- the core request
lifecycle code only needs to know how to send a signal, not how to talk to
OpenTelemetry.

A new, dedicated app
~~~~~~~~~~~~~~~~~~~~~

A new Django app (working name: ``opentelemetry``) would own all OTel-specific code:

#. The app defines and imports the ``Signal()`` instances that the rest of the
   codebase fires (or, alternatively, subscribes to signals already defined
   elsewhere, if the request lifecycle already emits its own domain events).
#. Inside that app, signal receivers translate each signal into an OTel span: they
   open a span when a step starts, set ``gen_ai.*`` (or otherwise appropriate)
   attributes from the signal payload, and close the span when the step completes or
   raises.
#. The app owns OTel SDK configuration -- tracer provider setup, resource
   attributes (service name, deployment environment), and the OTLP exporter
   endpoint -- so that this configuration lives in one place and can be toggled
   per-environment.

This keeps "does Smarter support OpenTelemetry" reducible to a fairly small,
self-contained unit: a Django app that subscribes to the signals the rest of the
platform already fires (or is extended to fire) and turns them into spans.

Proposed trace structure
~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming instrumentation is implemented via Django Signals, a single LLM request
would produce a trace shaped roughly like this:

.. code-block:: text

   Trace
   |---- LLMClient.run()
          |---- Guardrail.input()
          |---- Prompt.render()
          |---- Provider.request()
          |      |---- Tool.search()
          |      |---- Tool.weather()
          |      |---- Tool.database()
          |---- Guardrail.output()
          |---- Response

Each node corresponds to a signal/receiver pair and becomes a child span of
``LLMClient.run()``. Tool invocations (``Tool.search()``, ``Tool.weather()``,
``Tool.database()``, and any custom tools/plugins a Smarter user configures) are
children of ``Provider.request()`` since that's where tool-calling round-trips
happen.

Automatic instrumentation
~~~~~~~~~~~~~~~~~~~~~~~~~~

The custom, signal-driven spans above cover Smarter-specific business logic. They
would sit alongside, not replace, off-the-shelf auto-instrumentation for the parts of
the stack that already have mature OTel support:

* `opentelemetry-instrumentation-django
  <https://pypi.org/project/opentelemetry-instrumentation-django/>`_ for HTTP
  request/response spans and database query spans.
* Provider-specific instrumentation (for example OpenAI/Anthropic client
  instrumentation) where available, to capture token usage and request/response
  metadata without Smarter having to compute it itself.

UI surface (proposed, not finalized)
--------------------------------------

Two places in the product would need new UI:

Django admin
~~~~~~~~~~~~~

* A configuration model/panel for OTel export settings: enable/disable, OTLP
  endpoint, headers/auth, sampling rate.
* Read-only visibility into recent trace/span records if Smarter chooses to persist
  a local copy, versus relying entirely on an external backend.

Web console (this page's eventual host application)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* A per-account or per-plugin toggle for enabling tracing.
* A settings screen for pointing at an OTLP collector endpoint.
* Possibly a lightweight in-console trace viewer for the most recent requests,
  though the working assumption is that most users will forward traces to a backend
  they already operate rather than Smarter reinventing a trace UI.

Open questions
----------------

* Whether trace context should propagate across Smarter's multi-tenant boundary
  (that is, whether tenant/account identifiers belong in resource attributes, span
  attributes, both, or neither).
* Whether Smarter persists any span data itself, or is purely an emitter that assumes
  an external collector.
* Whether metrics (token counts, latency, cost) are covered by this same
  effort or tracked separately.
* Naming and final shape of the new Django app and its signals.

These, and anything else, are exactly what the linked discussion is for.

Related links
----------------

* `GitHub Discussion #722: Add OpenTelemetry Support
  <https://github.com/smarter-sh/smarter/discussions/722>`_
* `OpenTelemetry - What is OpenTelemetry?
  <https://opentelemetry.io/docs/what-is-opentelemetry/>`_
* `OpenTelemetry semantic conventions for Generative AI systems
  <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md>`__
* `OpenTelemetry Python SDK documentation
  <https://opentelemetry-python.readthedocs.io/en/latest/>`_
* `opentelemetry-instrumentation-django (PyPI)
  <https://pypi.org/project/opentelemetry-instrumentation-django/>`_
* `OTLP exporter specification
  <https://opentelemetry.io/docs/specs/otlp/>`_
* `Django Signals documentation
  <https://docs.djangoproject.com/en/stable/topics/signals/>`_
* `Smarter on GitHub <https://github.com/smarter-sh/smarter>`_
