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
  exact version by ``pip-compile``, in ``smarter/requirements/docker.txt``. This is the largest set
  of dependencies, and the one that runs with the most privilege.
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
- **Pinned GitHub Actions,** by commit SHA, and Dependabot pull requests for the Actions, the
  console's npm packages and the Helm chart's dependencies.
- **Image scanning.** Each environment's ECR repository scans every pushed image for known
  vulnerabilities.
- **A signed Helm chart.** Each release's chart is signed with Cosign; Artifact Hub shows the
  signature and the public key.
- **A signed extension registry.** The index of LLM tool extensions is signed, and Smarter checks the
  signature on every read. See :doc:`../llm-providers-and-extensions/extensions`.
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

The items below are listed in the order the project plans to work on them. The first is the most
serious. The others are cheaper, and the project expects to finish most of them first.

Outbound HTTPS is open to any address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The application's pods may connect to any address on the internet on ports 443, 80, 465, 587 and
3306. Most malicious packages send what they steal with an ordinary HTTPS request, so the network
policies don't stop it. DNS lookups, which the pods need, are a second, slower way out.

The platform can't simply close port 443, because several features call hosts that a manifest
author or the LLM chooses: API plugins, MCP clients, web search and LLM providers at custom
endpoints.

**Plan:**

- Move the features that call arbitrary hosts into a worker of their own, which holds no secrets
  other than the ones each call needs, and no AWS role.
- Limit the outbound traffic of every other pod to a list of known hosts (the LLM providers, AWS,
  SES), with an egress proxy or with DNS-aware network policies, which Calico's open-source edition
  doesn't support.
- Close the ports that each workload doesn't use: SES needs only one of 465 and 587, and 80 and 3306
  are needed only where plugins run.

Every application pod holds every credential
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The app, the workers, beat and the init Job read the same Secret and run as the same ServiceAccount,
so a dependency that is compromised in any of them reaches all of the platform's credentials.

**Plan:** split the credentials by workload, with a ServiceAccount, an IAM role and a Secret for each,
so that each pod holds only what it uses. This goes together with the separate worker above.

The Python pins don't have hashes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The lockfile pins each package's version, but not the hash of its file. If a package's file on PyPI,
or on the way from PyPI, were replaced, the build would install it.

**Plan:** generate the lockfile with ``pip-compile --generate-hashes``, and install with
``--require-hashes``, so that the build fails on any file it hasn't seen before.

Python dependencies aren't checked for advisories or updated automatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dependabot covers the npm packages, the GitHub Actions and the Helm chart, but not the Python
packages, and no check of the lockfile against published advisories runs in the pipeline. Image
scanning in ECR finds some of them, after the image is built.

**Plan:**

- Add the Python packages to Dependabot.
- Run ``pip-audit`` against the lockfile in the test workflow, so that a pull request that adds a
  package with a known vulnerability fails.

New releases are adopted as soon as they are published
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most malicious releases are found and removed from PyPI within days. A lockfile update can pick one
up in that window.

**Plan:** wait a few days before adopting a new release, with Dependabot's cooldown setting, except
for security fixes.

There is no software bill of materials, and the image isn't signed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Helm chart is signed, but the Docker image is not, and releases don't publish a software bill of
materials (SBOM). An operator can't verify that the image they run is the one the pipeline built, or
check its contents with their own tools without pulling it.

**Plan:**

- Generate an SBOM of each release's image and publish it with the release.
- Sign the image with Cosign, as the chart is, and document how to verify it.

What operators can do now
-------------------------

- **Review the lockfile** of the release you deploy, and scan its image with your own tools.
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

See also the :doc:`security-faq`.
