Application Security
====================

How the application and its Helm chart control what each request, user, API key and LLM tool can
do, and how they protect the platform's data.

The Web Console and the APIs
----------------------------

The web console
~~~~~~~~~~~~~~~

The web console is a single-page React application (:doc:`ADR-035 <../../../adr/035-single-page-app>`),
served by Django. It reads and writes through the **web console API**, under ``/api/web/``, which is
internal to the console:

- **Session authentication and CSRF.** The console calls the API with the browser's Django session
  cookie and a CSRF token. ``GET /api/web/session/`` describes the session and sets the CSRF cookie;
  every request that changes something must send the token in ``X-CSRFToken``. The session cookie is
  ``Secure``, ``HttpOnly`` and ``SameSite=Lax``, and sessions are stored in Redis, not in the cookie.
- **Signed-in users only.** Every page and every list endpoint requires a signed-in user, and its
  responses are never cached.
- **Ownership.** A list endpoint returns only the resources that the user owns or that are shared
  with them, by the same ownership rules as the REST API.

See :doc:`../tools/smarter-web-console` and
:doc:`../../../smarter-framework/developer-reference/react-integration`.

The REST API and deployed LLMClients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **API keys.** The REST API (``/api/v1/``), which the ``smarter`` CLI and the SDKs use,
  authenticates with Smarter API keys, sent as ``Authorization: Token <key>``. Smarter's
  authentication class, built on `Django REST Knox <https://jazzband.github.io/django-rest-knox/>`__,
  also checks that the key is active, journals each use, and warns about keys past their maximum
  lifetime. Every endpoint requires authentication unless it says otherwise.
- **Rate limiting.** Every API is rate limited, per user and, for anonymous clients, per IP address,
  including the APIs that a deployed LLMClient serves to the pages that embed it. A client over its
  limit gets HTTP 429 with a ``Retry-After`` header. The limits are
  ``SMARTER_APP_API_THROTTLE_RATE_USER`` (default ``600/minute``) and
  ``SMARTER_APP_API_THROTTLE_RATE_ANON`` (default ``120/minute``); ``none`` disables one. See
  `throttling.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/drf/throttling.py>`__.
- **JSON only.** API errors are always JSON, never Django's HTML error pages, and Pydantic
  ``SecretStr`` keeps secrets out of API responses.

Signing in
~~~~~~~~~~

Users sign in with a password, or with Google or GitHub (social auth). The authentication backends
are:

.. code-block:: python

   AUTHENTICATION_BACKENDS = [
       "social_core.backends.google.GoogleOAuth2",
       "social_core.backends.github.GithubOAuth2",
       "django.contrib.auth.backends.ModelBackend",
   ]

A deployment can replace them with ``DJANGO_AUTHENTICATION_BACKENDS``, e.g. with the multitenant
backends in ``smarter.lib.social_core.backends.multitenant`` (see :doc:`../../overrides`). Passwords must
pass Django's four validators: similarity to the user's attributes, minimum length, common
passwords, and all-numeric. See :doc:`../accounts-and-access/user-management`.


Smarter's middleware
--------------------

Smarter adds its own middleware where an AI platform, which serves many customer domains, needs more
than Django's. The full chain is ``MIDDLEWARE`` in
`settings/base.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/settings/base.py>`__.

- **Host validation and security headers.** ``SmarterSecurityMiddleware`` replaces Django's
  ``SecurityMiddleware``. It is first in the chain, and rejects with a 400 any request for a host
  that Smarter doesn't serve (the platform's own hosts, or a deployed LLMClient's domain) before
  anything queries the database. See
  `security.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/middleware/security.py>`__.
- **CORS.** ``SmarterCorsMiddleware`` replaces django-cors-headers' middleware, and allows each
  deployed LLMClient's own origins. See
  `cors.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/cors.py>`__.
- **Sensitive file blocking.** Requests for ``.env``, ``.git`` and similar files are refused. See
  `sensitive_files.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/sensitive_files.py>`__.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-sensitive-file-blocking.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Sensitive File Blocking"/>

- **Excessive 404 protection.** A client that requests many pages that don't exist, as scanners do,
  is blocked. See
  `excessive_404.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/excessive_404.py>`__.
- **CSRF for deployed LLMClients.** ``SmarterCsrfViewMiddleware`` computes the trusted origins for
  each request, so a deployed LLMClient's own domains are trusted, then hands the check to Django's
  CSRF middleware. It exempts a deployed LLMClient's chat API and requests from inside the cluster's
  network. See
  `csrf.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/csrf.py>`__.
- **JSON errors.** ``SmarterJsonErrorMiddleware`` returns API errors as JSON. See
  `json.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/lib/django/middleware/json.py>`__.

Django's protections
--------------------

- **HTTPS.** Traefik redirects HTTP and sets HSTS (see :doc:`infrastructure`), so ``SECURE_SSL_REDIRECT`` and
  ``SECURE_HSTS_SECONDS`` stay unset in Django. Django learns that a request was HTTPS from
  ``X-Forwarded-Proto`` (``SECURE_PROXY_SSL_HEADER``).
- **Cookies.** The session and CSRF cookies are ``Secure`` and ``SameSite=Lax``; the session cookie is
  also ``HttpOnly``.
- **Content Security Policy,** in **report-only** mode: browsers block nothing yet, and report what
  the policy would block, which Smarter logs. Inline scripts carry a nonce. The policy will be
  enforced once the reports are clean. See ``SECURE_CSP_REPORT_ONLY`` in ``settings/base.py``.
- **Clickjacking** protection with ``X-Frame-Options``.
- **SQL injection:** Smarter queries its own database through Django's ORM.
- **XSS:** Django's templates escape their output, and React escapes what it renders.
- **The secret key.** ``DJANGO_SECRET_KEY`` signs sessions and password reset tokens. Outside the
  local environment, Smarter refuses to start if it is missing or still a ``SET-ME`` placeholder.

AI-specific protections
-----------------------

- **Guardrails** inspect what passes between users and LLMs: they redact PII and secrets, and block
  prompt injection, jailbreaks and off-topic requests, before a message reaches the LLM or its tools,
  and before a reply reaches the user. See :doc:`../../../smarter-resources/smarter-guardrail`.
- **Server-side request forgery.** Tools that fetch URLs chosen by a manifest author or by the LLM
  (web search, skills, image search, MCP clients, API plugins, the extension registry, ...) go through
  one hardened client, ``safe_http``: HTTPS on port 443 only, only to public addresses, with every
  redirect validated, no credentials in URLs, credential headers dropped on a redirect to another
  host, bounded response sizes and timeouts. This keeps them away from the cluster's own network and
  the cloud's instance metadata. An ApiConnection's api may also use plain HTTP and its own port, but
  only at a public address. In the local environment, a developer's MCP clients and API connections
  may also reach ``localhost``. See
  `safe_http.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/plugin/safe_http.py>`__.
- **Signed extensions.** The extension registry's index is signed, and Smarter verifies its signature
  with ``SMARTER_APP_LLMTOOL_EXTENSION_REGISTRY_PUBLIC_KEY`` on every read. See :doc:`../llm-providers-and-extensions/extensions`.
- **Cost accounting.** The cost of every request to an external service, LLM providers included, is
  recorded per account. See :doc:`../costs-and-auditing/cost-accounting`.


Data Protection
---------------

- **In transit:** HTTPS for every request from outside the cluster; SMTP with TLS through SES;
  HTTPS for every call to an LLM provider.
- **Smarter Secrets** (the API keys and passwords that resources use, see
  :doc:`../../../smarter-resources/smarter-secret`) are encrypted with Fernet before they are saved, with
  ``SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY``. Only the encrypted value is in the database, and in its
  backups. Keep the key: without it, a restored database's Secrets can't be read (see
  :doc:`../operations/backup-and-restore`).
- **API keys** are stored as a digest. The key itself is shown once, when it is created, and may be
  given an expiry. See :doc:`../accounts-and-access/api-keys`.
- **Backups** go to a private S3 bucket that blocks public access, refuses unencrypted connections,
  encrypts objects (AES-256) and keeps versions.
- **Users' data exports** go to a second private bucket, encrypted, downloaded with presigned links
  that expire after 24 hours, and deleted by a lifecycle rule.
- **The environment's public bucket** serves static files and media uploads through CloudFront, and
  is public-read by design. Don't upload anything there that isn't meant to be public.

Not encrypted by default: Kubernetes Secrets at rest with a KMS key (``eks_create_kms_key`` in
smarter-infrastructure's ``stack.hcl``), and the MariaDB volume, whose ``gp3`` storage class doesn't
set ``encrypted``, unless your AWS account enables EBS encryption by default. Turn both on if your
policies require encryption at rest.


Audit Logging and Logs
----------------------

- **The Smarter Journal** keeps the platform's API responses, with who made each request, for long-term
  audit. It is turned on at run time with its waffle switch. See :doc:`../costs-and-auditing/smarter-journal`.
- **Application logs** go to Loki in the cluster, with Alloy collecting them from every pod. Smarter
  never writes a secret, credential or PII to its log: it logs ids and masked values. In DEBUG mode
  the web console shows the log to users, which is one more reason to keep DEBUG off in production.
  See :doc:`../../configuration`.
- **Traefik's access log** records every request that reaches the cluster.


Secure Development
------------------

Every change to Smarter passes `bandit <https://bandit.readthedocs.io/>`__, mypy and the other
pre-commit hooks, and GitHub's CodeQL analysis. Dependabot opens pull requests for the console's npm
packages, the GitHub Actions and the Helm chart's dependencies, once a release has been published for
two weeks. Every Python package is pinned to an exact version, and updated by a maintainer, and every
pull request fails when a pinned package has a published vulnerability (``pip-audit``). Every Docker
image is built with the operating system's latest security updates. The repository is public, so its
code, infrastructure and these settings are open to review.

:doc:`supply-chain` describes the risk of a malicious dependency in detail: what a
compromised package could reach, what protects against it, and the weaknesses that the project plans
to fix.
