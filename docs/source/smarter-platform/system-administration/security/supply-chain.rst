Supply-Chain Security
=====================

A supply-chain attack reaches a platform through something it depends on rather than through the
platform itself: a malicious release of a Python package, a typosquatted name, a package maintainer's
stolen account, a compromised base image or GitHub Action. The attacker's code then runs inside the
platform, with the platform's own permissions.

This is an assessment of Smarter's supply-chain risk, including its known weaknesses and the plan
to fix each one.

Open source and supply-chain risk
---------------------------------

Because Smarter is open source, anyone can verify its supply chain: exactly which packages it
installs, at which versions, and every control described here, in the code itself:

- the Python lockfile, `smarter/requirements/docker.txt <https://github.com/smarter-sh/smarter/blob/main/smarter/requirements/docker.txt>`__;
- the image build, the `Dockerfile <https://github.com/smarter-sh/smarter/blob/main/Dockerfile>`__
  and `build.yml <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/build.yml>`__;
- the network policies, in smarter-infrastructure's
  `network_policy.tf <https://github.com/smarter-sh/smarter-infrastructure/blob/main/aws/terraform/kubernetes/network_policy.tf>`__.

What Smarter depends on
-----------------------

- **Python packages.** Every package in the Docker image, direct and transitive, is pinned to an
  exact version and the hashes of its files, in ``smarter/requirements/docker.txt``. This is the
  largest set of dependencies, and the one that runs with the most privilege.
- **Extensions,** third-party Python code that the platform installs at run time from the signed
  extension registry, and runs to answer tool calls (below).
- **The web console's npm packages,** in the
  `smarter-console <https://github.com/smarter-sh/smarter-console>`__ repository. They run in users'
  browsers, not on the server. The platform installs the console's built release, pinned in
  ``smarter-console-version.txt``.
- **The base image,** the official Python image, pulled from the ECR Public Gallery, with the
  operating system's latest security updates applied at each build.
- **GitHub Actions,** each pinned to a commit SHA rather than a tag, so that a moved tag can't change
  what runs in the pipeline.
- **The Helm chart's dependencies,** the MariaDB, Redis and Loki subcharts, and the third-party images
  they run, which the cluster pulls through an ECR pull-through cache.

Where a malicious dependency would run
--------------------------------------

**At build time.** A Python package can run code when it is installed. The image's ``pip install``
runs inside Docker's build, on GitHub's runners. That build doesn't receive the workflow's AWS
credentials, but anything the code does is written into the image that every environment then runs.

**At run time,** which is the larger exposure. A Python package runs inside the Django and Celery
processes, as part of the application. Containers and network policies don't separate it from
Smarter's own code. It can reach everything the application can:

- the pods' environment, from the Kubernetes Secret that every pod reads: the database password, the
  Fernet key that encrypts Smarter Secrets, the LLM providers' API keys and the SES SMTP password;
- the AWS permissions of the pods' IAM role (Route53, ACM, the environment's S3 buckets and LLMHost
  node groups), through AWS's APIs;
- the ServiceAccount's Kubernetes Role in the namespace, which includes Secrets;
- the database, Redis and the internet on HTTPS (below).

What protects against it today
------------------------------

- **Exact pins.** No dependency changes without a commit that changes the lockfile, which is public
  and reviewed. A malicious new release of a package isn't installed until the lockfile is updated to
  it.
- **Hashes.** The lockfile also has the sha256 of each of a release's files, its wheels and its
  sdist, which ``make python-requirements`` reads from PyPI. The Docker build installs with
  ``--require-hashes``, so a file that was replaced on PyPI, or on the way from it, fails the build,
  and so does a lockfile written without hashes. ``pip`` and ``setuptools`` are pinned and hashed
  too.
- **Pinned GitHub Actions,** by commit SHA.
- **Dependabot pull requests** for the GitHub Actions, the npm packages and the Helm chart's
  dependencies, once a release has been published for two weeks. Most malicious releases are found and
  removed from their registry within days. Security updates are proposed at once. The Python packages
  are left out on purpose: Dependabot's changes to the ``pip-compile`` lockfiles left pip unable to
  install them. A maintainer updates the Python lockfile with ``make python-requirements``, and the
  change passes the tests like any other.
- **Two weeks' wait for Python releases, too.** ``make python-requirements`` ends with
  ``make python-cooldown``, which fails when the lockfile pins a release uploaded to PyPI in the last
  14 days. The project's own packages, such as ``smarter-types``, are exempt, and a security fix that
  can't wait is allowed by name (``PYTHON_COOLDOWN_ALLOW``). See ``scripts/python_lockfiles.py``.
- **An advisory check on every pull request.** ``make python-audit`` checks the Python lockfiles
  against PyPI's and OSV's published advisories with ``pip-audit``, and the test workflow fails when
  one pins a release with a known vulnerability. It runs even when nothing in the lockfile changed,
  because new advisories are published against old releases. An advisory that doesn't reach Smarter,
  such as one in a part of a package that Smarter never imports, is ignored by its id in the
  ``Makefile``, with the reason, until the package is upgraded past it.
- **Image scanning.** Each environment's ECR repository scans every pushed image for known
  vulnerabilities.
- **A signed Helm chart and a signed image.** Each release's chart and Docker image are signed with
  Cosign, with the same key, and each signature is recorded in Sigstore's public transparency log.
  Artifact Hub shows the chart's signature and the public key. See `Verifying a release`_.
- **A software bill of materials.** Each image carries an SBOM (SPDX) and a SLSA build provenance for
  each platform, attached by BuildKit at build time and covered by the image's signature. Each
  release on GitHub also has the SBOMs as files, ``smarter-<version>-amd64.spdx.json`` and
  ``smarter-<version>-arm64.spdx.json``, so that the image's contents can be checked without pulling
  it.
- **A signed extension registry.** The index of LLM tool extensions is signed, and Smarter checks the
  signature on every read, so an Extension comes from the publisher the index names. The signature
  doesn't vouch for the Extension's code: see the second weakness below, and
  :doc:`../llm-providers-and-extensions/extensions`.
- **Hardened containers.** The pods run as a non-root user, on a read-only root filesystem, with
  every Linux capability dropped. Code can't modify the installed packages or the image at run time,
  which makes it harder for an attack to persist.
- **No long-lived AWS keys in the pods,** other than the SES SMTP password. AWS permissions come from
  short-lived IRSA credentials, scoped to one environment.
- **Network policies limit movement inside the cluster.** Calico's policies keep a compromised pod
  away from other namespaces, and every pod outside the platform away from MariaDB and Redis, and
  they block outbound connections on ports the platform doesn't use. They are not an exfiltration
  control: see the first weakness below.
- **Code analysis.** CodeQL and bandit run on every change. They check Smarter's own code, not its
  dependencies.

Known weaknesses, and the plan for each
---------------------------------------

Two weaknesses remain, and the same change addresses both: the tool calls that reach hosts chosen by a
manifest author or the LLM move to a worker with no credentials, and every other pod's internet traffic
is limited to known hosts. :doc:`ADR-038 </adr/038-tool-isolation-and-egress>` proposes the design and
the order of the work.

Outbound HTTPS is open to any address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The application's pods may connect to any address on the internet on ports 443, 80, 587 and 3306.
Most malicious packages send what they steal with an ordinary HTTPS request, so the network
policies don't stop it. DNS lookups, which the pods need, are a second, slower way out.

The platform can't simply close port 443, because several features call hosts that a manifest
author or the LLM chooses: API plugins, MCP clients, web search and LLM providers at custom
endpoints.

**Plan:**

- Move the features that call arbitrary hosts (API, SQL and web search plugins, MCP clients and
  Extensions) into a worker of their own, which holds no secrets other than the ones each call needs,
  no database access and no AWS role.
- Limit the outbound traffic of every other pod to a list of known hosts (the LLM providers, AWS,
  GitHub), through an egress proxy in the cluster. DNS-aware network policies would do the same in the
  network, but Calico's open-source edition doesn't support them.
- Close 80 and 3306 for every pod but that worker: they are needed only where API plugins on plain
  HTTP and SQL plugins run. The SMTP port that Smarter doesn't use, 465, is already closed: SES is
  reached on 587 only.

Every application pod holds every credential
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The app, the workers, beat and the init Job read the same Secret and run as the same ServiceAccount,
so a dependency that is compromised in any of them reaches all of the platform's credentials.

This includes Extensions. An Extension's code is third-party Python, which the app imports into its
own process at run time to answer a tool call, where it can read every credential. The registry's
signature says who published an Extension, not what its code does. Install only Extensions whose code
you have read.

**Plan:** run tool calls, Extensions included, in the worker above, which holds no credentials, and
split the remaining credentials by workload, with a ServiceAccount, an IAM role and a Secret for each,
so that each pod holds only what it uses. See :doc:`ADR-038 </adr/038-tool-isolation-and-egress>`.

What operators can do now
-------------------------

- **Verify the release you deploy,** as below, and deploy the image by its digest, not by a tag.
- **Review the lockfile** of the release you deploy, and scan its image, or its SBOM, with your own
  tools.
- **Close the ports you don't use.** If your platform doesn't use SQL plugins, or API plugins on plain
  HTTP, remove the 3306 and 80 rules from the application's egress policy.
- **Turn on threat detection.** Amazon GuardDuty notices unusual API calls made with the pods'
  credentials, and unusual DNS and network traffic. See "What Smarter Doesn't Provide" in
  :doc:`infrastructure`.
- **Rotate credentials** after any suspected compromise: the LLM providers' keys, the SES user's key,
  the database password, and Smarter Secrets. Keep the Fernet key, or the Secrets that are already
  stored can't be read.
- **Update regularly,** as :doc:`../operations/updates` describes, so that fixed dependencies reach
  your platform.

Verifying a release
-------------------

The project's public key is
`sigstore/artifacthub-cosign.pub <https://github.com/smarter-sh/smarter/blob/main/sigstore/artifacthub-cosign.pub>`__.
With `Cosign <https://docs.sigstore.dev/cosign/system_config/installation/>`__ installed, verify the
image you run, by its digest, and the chart:

.. code-block:: console

   curl -LO https://github.com/smarter-sh/smarter/raw/main/sigstore/artifacthub-cosign.pub
   cosign verify --key artifacthub-cosign.pub mcdaniel0073/smarter@sha256:<digest>
   cosign verify --key artifacthub-cosign.pub ghcr.io/smarter-sh/charts/smarter:<chart version>

The image's tags (``v0.49.0``, ``v0.49``, ``latest``, ...) all point to one signed digest, which
``docker buildx imagetools inspect mcdaniel0073/smarter:<version>`` prints. To read the SBOM or the
provenance from the image itself:

.. code-block:: console

   docker buildx imagetools inspect mcdaniel0073/smarter:<version> \
     --format '{{ json (index .SBOM "linux/amd64").SPDX }}'
   docker buildx imagetools inspect mcdaniel0073/smarter:<version> \
     --format '{{ json (index .Provenance "linux/amd64").SLSA }}'

Images built before signing was added have no signature or SBOM.

See also the :doc:`security-faq`.
