Smarter Architecture
====================

Smarter is a `Django <https://www.djangoproject.com/>`__ application, built in
four layers. Each layer depends only on the layers below it: Smarter's Django
apps use Smarter's own subsystems, which extend a handful of third-party
Django apps, which run on Linux.

.. code-block:: text

    ┌──────────────────────────────────────────────────────────────────────────────────────┐
    │  CLIENTS     smarter CLI  ·  REST /api/v1/cli/<cmd>/  ·  Web console (React apps)    │
    │              ·  deployed LLMClient hosts (django-hosts subdomains)                   │
    └───────────────────────────────────────────┬──────────────────────────────────────────┘
                                                │  HTTP
    ┌───────────────────────────────────────────▼──────────────────────────────────────────┐
    │ 4. SMARTER DJANGO APPS                           smarter/smarter/apps/<app>          │
    │                                                                                      │
    │  ┌─ Platform ──────────┐ ┌─ LLM runtime ───────────┐ ┌─ Tools & context ──────────┐  │
    │  │ account             │ │ llmclient (+Custom Dom.)│ │ llmtool    (plugins)       │  │
    │  │ api      (v1, cli)  │ │ llmhost                 │ │ connection (sql / api)     │  │
    │  │ dashboard (console) │ │ provider                │ │ mcpclient · mcpserver      │  │
    │  │ docs                │ │ prompt                  │ │ vectorstore · vectorsearch │  │
    │  │ secret              │ │ orchestrator            │ │ guardrail                  │  │
    │  └─────────────────────┘ │ proxy                   │ └────────────────────────────┘  │
    │                          └─────────────────────────┘                                 │
    │  ┌─ infrastructure ──────── facade: .dns .certificates .kubernetes .email ────────┐  │
    │  │   providers: AWS (Route53, ACM, EKS) · in-memory fake (tests)                  │  │
    │  └────────────────────────────────────────────────────────────────────────────────┘  │
    │  extensibility: Plugins, SAM manifests that configure built-in tool patterns         │
    │    (llmtool.plugin) · Extensions, Python packages that superusers install at         │
    │    run time from the signed registry (llmtool.extension) · MCP servers (mcpclient)   │
    └───────────────────────────────────────────┬──────────────────────────────────────────┘
    ┌───────────────────────────────────────────▼──────────────────────────────────────────┐
    │ 3. SMARTER SUBSYSTEMS                                 smarter/smarter/lib/*          │
    │                                                                                      │
    │ ┌─ SAM ─────────────────┐ ┌─ caching ──────┐ ┌─ logging ─────────┐ ┌─ journal ─────┐ │
    │ │ lib/manifest          │ │ lib/cache      │ │ lib/logging       │ │ lib/journal   │ │
    │ │ YAML manifest         │ │ Redis-backed   │ │ per-request log   │ │ (Django app)  │ │
    │ │  → loader             │ │ cache helpers  │ │ context           │ │ records every │ │
    │ │  → Pydantic models    │ │ & decorators   │ │ middleware,       │ │ API/CLI       │ │
    │ │  → controller         │ │                │ │ waffle-switched   │ │ request and   │ │
    │ │  → AbstractBroker     │ │                │ │ loggers           │ │ response      │ │
    │ │  (apply/get/describe/ │ │                │ │                   │ │               │ │
    │ │   delete/deploy)      │ │                │ │                   │ │               │ │
    │ └───────────────────────┘ └────────────────┘ └───────────────────┘ └───────────────┘ │
    │ supporting: lib/drf (Smarter auth tokens, token middleware) · lib/django (base       │
    │   models, views, middleware, waffle) · lib/celery_conf · lib/unittest · lib/typing   │
    └───────────────────────────────────────────┬──────────────────────────────────────────┘
    ┌───────────────────────────────────────────▼──────────────────────────────────────────┐
    │ 2. THIRD-PARTY DJANGO APPS AND FRAMEWORKS                                            │
    │                                                                                      │
    │ ┌───────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────┐ ┌───────────────┐│
    │ │ DRF           │ │ knox         │ │ Pydantic    │ │ waffle       │ │ Celery        ││
    │ │ REST views,   │ │ API-key      │ │ data        │ │ feature      │ │ async tasks,  ││
    │ │ serializers   │ │ token auth   │ │ models      │ │ flags and    │ │ beat (redbeat,││
    │ │ (+ drf_yasg)  │ │              │ │             │ │ switches     │ │ django_celery_││
    │ └───────────────┘ └──────────────┘ └─────────────┘ └──────────────┘ │ beat)         ││
    │                                                                     └───────────────┘│
    │ also: django_hosts · corsheaders · social_django · storages · taggit                 │
    │                                                                                      │
    │ Django  (admin, auth, contenttypes, sessions, messages, staticfiles, ...)            │
    └───────────────────────────────────────────┬──────────────────────────────────────────┘
    ┌───────────────────────────────────────────▼──────────────────────────────────────────┐
    │ 1. LINUX RUNTIME                                                                     │
    │                                                                                      │
    │  Debian (python slim) container image  ·  kubectl                                    │
    │  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────────┐ ┌──────────────────┐│
    │  │ smarter-app  │ │ smarter-beat │ │ smarter-worker            │ │ smarter-mariadb  ││
    │  │ (Django)     │ │ (Celery beat)│ │ smarter-worker-infra      │ │ smarter-redis    ││
    │  └──────────────┘ └──────────────┘ └───────────────────────────┘ └──────────────────┘│
    │  Production: Kubernetes (AWS EKS)                                                    │
    └──────────────────────────────────────────────────────────────────────────────────────┘

Linux
-----

Smarter ships as a single Docker image, built on the official Debian-based
Python slim image, with ``kubectl`` added so that the platform can manage the
Kubernetes resources of deployed applications. The same image runs as the
Django application server (``smarter-app``), the Celery workers
(``smarter-worker`` and ``smarter-worker-infrastructure``) and the Celery beat
scheduler (``smarter-beat``). MariaDB holds the data and Redis serves as both
the cache and the Celery message broker. In production all of these run on
Kubernetes. See :doc:`technologies/docker` and :doc:`smarter-on-kubernetes`.

Third-Party Django Apps
-----------------------

Smarter builds on Django and a short list of well-established third-party apps:

- `Pydantic <https://docs.pydantic.dev/>`__ validates the YAML manifests of every
  resource and provides the models that brokers use to implement the
  :doc:`Smarter API <smarter-api>`.
- `Django REST Framework <https://www.django-rest-framework.org/>`__ (DRF)
  provides the views and serializers of the :doc:`Smarter API <smarter-api>`.
- `knox <https://jazzband.github.io/django-rest-knox/>`__ provides the token
  authentication behind Smarter API keys.
- `taggit <https://django-taggit.readthedocs.io/>`__ lets every resource carry
  tags.
- `waffle <https://waffle.readthedocs.io/>`__ provides feature flags and
  switches, which also turn individual loggers on and off.
- `Celery <https://docs.celeryq.dev/>`__ runs long or periodic work, such as
  deploying an LLMClient or issuing a certificate, outside the request cycle.

Smarter Subsystems
------------------

The ``smarter.lib`` package holds the framework code that the Django apps share.
Four subsystems shape nearly every request:

- **SAM**, the Smarter Application Manifest. Every resource is declared in a
  YAML :doc:`manifest <smarter-manifests>` that a loader validates against
  Pydantic models and hands to a :doc:`broker <smarter-broker-model>`, which
  implements the ``apply``, ``get``, ``describe``, ``delete`` and ``deploy``
  commands for that kind of resource.
- **Caching** wraps Django's Redis cache with Smarter's own helpers and
  decorators. See :doc:`developer-reference/lib/caching`.
- **Logging** adds per-request context, such as the user, to every
  log line, and lets each logger be switched on with waffle. See
  :doc:`developer-reference/lib/logging`.
- **The journal** records every API and CLI request with its response, giving an
  audit trail of who changed what. See
  :doc:`developer-reference/smarter-journal`.

Smarter Django Apps
-------------------

Each family of resources is a Django app in ``smarter.apps``, with its models,
its SAM broker, its API views and its web console pages. The apps fall into
three groups:

- **Platform**: accounts and users (:doc:`../smarter-resources/smarter-account`),
  the API, the web console dashboard, the documentation pages, and
  :doc:`../smarter-resources/smarter-secret`.
- **LLM runtime**: :doc:`../smarter-resources/smarter-llmclient` with its
  :doc:`custom domains <../smarter-resources/smarter-custom-domain>`,
  :doc:`../smarter-resources/smarter-llmhost`,
  :doc:`../smarter-resources/smarter-provider`,
  :doc:`../smarter-resources/smarter-prompt`,
  :doc:`../smarter-resources/smarter-orchestrator` and
  :doc:`../smarter-resources/smarter-proxy`.
- **Tools and context**: :doc:`LLMTool plugins <../smarter-resources/smarter-llmtool>`,
  :doc:`../smarter-resources/smarter-connection`,
  :doc:`../smarter-resources/smarter-mcpclient`, the MCP server,
  :doc:`../smarter-resources/smarter-vectorstore`,
  :doc:`../smarter-resources/smarter-vectorsearch` and
  :doc:`../smarter-resources/smarter-guardrail`.

LLMs reach everything they don't already know through tools, and Smarter can be extended with
new tools in two ways: Plugins, YAML manifests that configure one of the ``llmtool`` app's
built-in tool patterns, and Extensions, Python packages in ``llmtool.extension`` that platform
superusers install at run time, from the web console's Extensions page, by upload or from the signed Smarter Extension registry.
MCP servers, through the ``mcpclient`` app, are a third source of tools. See :doc:`extensibility`.

The ``infrastructure`` app is the only part of Smarter that talks to the cloud.
It offers a single facade for DNS, TLS certificates, Kubernetes and email, with
an AWS provider for production and an in-memory provider for tests. See
:doc:`technologies/infrastructure`.
