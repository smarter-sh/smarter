:orphan:

Production Deployment
===================================

A production deployment of Smarter runs on Kubernetes, on any cluster: a cloud provider's managed
Kubernetes, or your own cluster, wherever it runs, including your own data center. At a high level,
you'll be performing the following three steps:

1. **Identify the common settings** that are needed by both the cloud infrastructure and the Kubernetes deployment.
2. **Build the cloud infrastructure**: the Kubernetes cluster, and for each environment its namespace,
   DNS, certificates, email, storage and credentials.
   `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__ builds all of it with
   Terraform on AWS, with Azure and Google Cloud to follow. On another cluster, you provide these yourself.
3. **Deploy the Kubernetes pods**, with the
   `Smarter Helm chart <https://artifacthub.io/packages/helm/project-smarter/smarter>`__: the
   application server, the Celery workers, Celery Beat, MariaDB and Redis.

The infrastructure must exist before the pods are deployed. The Helm chart installs into the
environment's namespace, and reads the database, administrator, email and Django credentials from the
Kubernetes Secrets there.


Step 1: Identify the common settings
------------------------------------

These are the root values used for naming key resources. smarter-infrastructure and the Helm chart each
need them, and they must agree. These values are not easily changed after a deployment, so choose them
carefully.

.. list-table::
   :header-rows: 1
   :widths: 20 24 28 28

   * - Value
     - Example
     - smarter-infrastructure ``.env``
     - Helm values
   * - Root domain
     - ``example.com``
     - ``ROOT_DOMAIN``
     - ``env.SMARTER_PLATFORM_ROOT_DOMAIN``
   * - Platform subdomain
     - ``platform``
     - ``PLATFORM_SUBDOMAIN``
     - ``env.SMARTER_PLATFORM_SUBDOMAIN``
   * - AWS region
     - ``ca-central-1``
     - ``AWS_REGION``
     - ``env.AWS_REGION``
   * - Environment
     - ``prod``, or ``alpha``, ``beta``, ``next``
     - one folder per environment, ``aws/environments/<environment>``
     - ``env.SMARTER_ENVIRONMENT``

A Route53 hosted zone for the root domain must already exist in your AWS account.


Step 2: Build the cloud infrastructure
--------------------------------------

smarter-infrastructure builds everything with `Terraform <https://developer.hashicorp.com/terraform>`__
and `Terragrunt <https://terragrunt.gruntwork.io/>`__, a wrapper that applies the same Terraform to
several environments. You don't need to change its code, apart from the one line below. Its
`README <https://github.com/smarter-sh/smarter-infrastructure>`__ and
`Makefile <https://github.com/smarter-sh/smarter-infrastructure/blob/main/Makefile>`__ explain each
command.

.. danger::

   **Running cloud infrastructure costs money.** The cluster, its nodes, the load balancer, CloudFront and
   the rest are billed by AWS from the moment they are created. Review AWS's pricing for each before you
   apply. Expect to spend at least a few hundred US dollars per month for a production deployment,
   and more if you run multiple environments. Delete the infrastructure when you don't need it, with
   ``make destroy`` in smarter-infrastructure.

1. Clone `smarter-infrastructure <https://github.com/smarter-sh/smarter-infrastructure>`__, and run
   ``make`` to create its ``.env``. Fill it in:

   .. list-table::
      :header-rows: 1
      :widths: 34 12 54

      * - Variable
        - Required
        - What it is
      * - ``ROOT_DOMAIN``, ``PLATFORM_SUBDOMAIN``, ``AWS_REGION``
        - yes
        - The common settings, from Step 1.
      * - ``AWS_ACCOUNT_ID``
        - yes
        - The AWS account.
      * - ``AWS_PROFILE``
        - yes
        - The AWS credentials that Terraform runs with, an administrator's.
      * - ``IAM_ADMIN_USER_ARN``
        - yes
        - The IAM user who administers the cluster.
      * - ``MYSQL_ROOT_USERNAME``, ``MYSQL_ROOT_PASSWORD``
        - yes
        - The database server's administrator.
      * - ``DOCKER_USERNAME``, ``DOCKER_PAT``
        - yes
        - A Docker Hub account and access token, for the cluster's image cache.
      * - ``UNIQUE_ID``
        - yes
        - A suffix that makes the cluster's name unique, e.g. the date, ``202602121853``.
      * - ``UPTIME_ALERT_EMAIL``
        - no
        - Where the uptime checks send their alarms.
      * - ``COST_CODE``
        - no
        - A tag on every resource. Default ``smarter``.

2. In ``aws/terraform/smarter/providers.tf``, set the Kubernetes provider's ``config_context`` to your
   cluster's kubeconfig context. It names the maintainers' cluster.
3. Build the shared infrastructure, once: the VPC, the Kubernetes cluster, then its ingress, certificate
   manager and descheduler. ``cd aws/stack && terragrunt run --all apply`` applies them in that order.
4. Build each environment. For an environment other than ``prod`` or ``alpha``, copy one of their folders
   under ``aws/environments/`` and change its ``environment``. Then
   ``cd aws/environments/<environment> && terragrunt apply``. This creates the environment's namespace,
   its Kubernetes Secrets, IAM roles, DNS zones, certificates, SES email, S3 buckets and CloudFront
   distribution.
5. Note three values for Step 3: the cluster's name, the output ``cluster_name`` of ``aws/stack/kubernetes``;
   and the IAM roles of the pods, one per kind of pod, and of the nightly database backup, the outputs
   ``smarter_pod_iam_role_arns`` and ``smarter_backup_iam_role_arn`` of
   ``aws/environments/<environment>``. Read each with ``terragrunt output <name>`` in its folder.

.. warning::

   Don't build or change these resources by hand. They depend on each other, and Terraform tags each one,
   which is how you find them in your AWS account afterwards.


Step 3: Deploy the Kubernetes pods
----------------------------------

The Helm chart installs Smarter into the environment's namespace. It reads the database, administrator,
email and Django credentials from the Kubernetes Secrets that smarter-infrastructure created there, so
your values file holds only the settings below.

.. tip::

   The smarter repository's GitHub Actions workflow
   `Deploy <https://github.com/smarter-sh/smarter/blob/main/.github/workflows/deploy.yml>`__ already does
   every part of this step: it connects to the cluster, writes the values file from GitHub Actions
   secrets, and runs ``helm upgrade --install``, on every release. Use it as the model for automating your
   own deployments.

1. On the computer that you run ``helm`` from, connect ``kubectl`` and ``helm`` to the cluster. On AWS:

   .. code-block:: bash

      aws eks update-kubeconfig --region <region> --name <cluster name>

2. On that computer, create a file named ``my-values.yaml``, in any folder.
   The next step passes it to ``helm``. It holds API keys, so don't commit it to a repository.

   **This is the minimum set of values.** On a cluster that smarter-infrastructure built, the deployment needs each
   of these values.

   .. code-block:: yaml

      env:
        SMARTER_ENVIRONMENT: "prod"
        SMARTER_PLATFORM_ROOT_DOMAIN: "example.com"
        SMARTER_PLATFORM_SUBDOMAIN: "platform"
        AWS_REGION: "ca-central-1"
        SMARTER_SUBSYSTEM_K8S_CLUSTER_NAME: "smarter-platform-ca-202602121853"
        SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY: "<a URL-safe base64-encoded 32-byte key>"
        DOCKERHUB_USERNAME: "<DOCKER_USERNAME>"
        DOCKERHUB_PAT: "<DOCKER_PAT>"
      bootstrapSecrets:
        openai_api_key: "<your OpenAI API key>"
      serviceAccount:
        awsRoleArns:
          api: "<smarter_pod_iam_role_arns.api>"
          worker: "<smarter_pod_iam_role_arns.worker>"
          worker-infrastructure: "<smarter_pod_iam_role_arns.worker-infrastructure>"
          job-init: "<smarter_pod_iam_role_arns.job-init>"
        createClusterRole: false
      databaseScheduledBackup:
        awsRoleArn: "<smarter_backup_iam_role_arn>"

   .. list-table::
      :header-rows: 1
      :widths: 42 58

      * - Value
        - What it is
      * - ``env.SMARTER_ENVIRONMENT``, ``_PLATFORM_ROOT_DOMAIN``, ``_PLATFORM_SUBDOMAIN``,
          ``env.AWS_REGION``
        - The common settings, from Step 1.
      * - ``env.SMARTER_SUBSYSTEM_K8S_CLUSTER_NAME``
        - The cluster's name, from Step 2. Smarter deploys LLMClients into it.
      * - ``serviceAccount.awsRoleArns``, ``databaseScheduledBackup.awsRoleArn``
        - The IAM roles, from Step 2: one per kind of pod that calls AWS, with only what it does there,
          and the backup's. Celery Beat and the migrate Job have none. ``createClusterRole: false``:
          smarter-infrastructure has already created the pods' cluster roles.
      * - ``env.SMARTER_PLATFORM_FERNET_ENCRYPTION_KEY``
        - The key that Smarter encrypts Secrets with. Without it, each pod generates its own key, and a
          Secret saved by one pod can't be read by another, or after a restart.
      * - ``env.DOCKERHUB_USERNAME``, ``env.DOCKERHUB_PAT``
        - The Docker Hub account from Step 2, which pulls Smarter's image. Only the chart's image-pull
          Secret holds them: unlike the rest of ``env``, they reach no pod's environment.
      * - ``bootstrapSecrets.openai_api_key``
        - OpenAI is the default LLM provider, and the example resources and Stackademy use it. Each key
          under ``bootstrapSecrets`` becomes a Smarter Secret of that name, owned by the Smarter admin. The
          chart puts them in the Kubernetes Secret ``smarter-bootstrap-secrets``, which only the init job
          mounts, and ``manage.py initialize_bootstrap_secrets`` creates the Smarter Secrets from it. No
          other pod receives them, as environment variables or files.

   **What else can go in the file.** Five kinds of values, each to change a default or turn on a feature:

   .. list-table::
      :header-rows: 1
      :widths: 22 30 48

      * - Kind
        - In the file
        - Where to find the names
      * - Smarter settings
        - ``env.SMARTER_<SETTING>``
        - The chart's `values.yaml <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml>`__ lists every one, with its default, spelled exactly as your file must spell
          it. ``SMARTER_PLATFORM_ROOT_DOMAIN`` sets the setting ``platform_root_domain``, and so on, which
          :doc:`../../smarter-framework/developer-reference/smarter-settings` describes.
      * - Resource types, on or off
        - ``env.SMARTER_APP_<APP>_ENABLE``
        - :ref:`sam-app-feature-flags`, in :doc:`../configuration`.
      * - Django settings
        - ``env.DJANGO_<SETTING>``
        - Any setting of Django, or of a Django package that Smarter uses:
          `Django's settings reference <https://docs.djangoproject.com/en/6.0/ref/settings/>`__. Yours
          replaces Smarter's value outright; read :doc:`../overrides` first.
      * - The chart's own options
        - top-level keys, e.g. ``app``, ``hpa``, ``worker``, ``beat``, ``databaseInit``,
          ``databaseScheduledBackup``, ``slackBot``, ``bootstrapSecrets``
        - The chart's `values.yaml <https://github.com/smarter-sh/smarter/blob/main/helm/charts/smarter/values.yaml>`__: replicas, resources, autoscaling, the init job, the nightly backup, and the
          Slack bot.
      * - MariaDB and Redis
        - ``mariadb.*``, ``redis.*``
        - The Bitnami charts that the chart installs them with:
          `mariadb <https://artifacthub.io/packages/helm/bitnami/mariadb>`__ and
          `redis <https://artifacthub.io/packages/helm/bitnami/redis>`__.

   The Smarter settings that most deployments add:

   .. list-table::
      :header-rows: 1
      :widths: 42 58

      * - Value
        - What it is
      * - ``env.SMARTER_PLATFORM_EMAIL_ADMIN``
        - The administrators' email address.
      * - ``env.SMARTER_PLATFORM_BRANDING_*``
        - Your organization's name, address, support email, contact URL and logo, as the web console and
          its emails show them. Unset, they show The Smarter Project's.
      * - ``bootstrapSecrets.anthropic_api_key``, ``gemini_api_key``, ``mistral_api_key``, ...
        - The other LLM providers. The chart's ``values.yaml`` lists every Secret name.
      * - ``bootstrapSecrets.google_maps_api_key``, ``tavily_api_key``, ``brave_search_api_key``,
          ``pinecone_api_key``
        - Tools and vector stores that the example resources use.
      * - ``env.SMARTER_SUBSYSTEM_SOCIAL_AUTH_*``
        - Sign-in with Google, GitHub or LinkedIn.
      * - ``env.SMARTER_SUBSYSTEM_SLACK_BOT_TOKEN``, ``databaseInit.notifySlackChannel``
        - The init job's and the nightly backup's notices in Slack.
      * - ``env.SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD``
        - A read-only database account for the nightly backup. Unset, the backup uses the root account.

3. Install the chart into the environment's namespace, ``smarter-<subdomain>-<environment>``:

   .. code-block:: bash

      helm upgrade --install smarter oci://ghcr.io/smarter-sh/charts/smarter \
        --version <chart version> \
        --namespace smarter-platform-prod \
        --values my-values.yaml \
        --timeout 900s

   The chart versions are listed on
   `Artifact Hub <https://artifacthub.io/packages/helm/project-smarter/smarter>`__. To upgrade, run the
   same command with the new version.

On a fresh install, the pods wait until the chart's init job has created and migrated the database. The
init job then runs ``manage.py initialize_platform``, which creates the administrator, the built-in
providers, the example resources and Stackademy. See
:doc:`../../smarter-framework/smarter-on-kubernetes`.

When it's done, sign in at ``https://<subdomain>.<root domain>/``, e.g. ``https://platform.example.com/``,
as ``admin``, with the password in the Kubernetes Secret ``smarter-admin``:

.. code-block:: bash

   kubectl get secret smarter-admin -n smarter-platform-prod \
     -o jsonpath='{.data.SMARTER_ADMIN_PASSWORD}' | base64 --decode

.. figure:: https://cdn.smarter.sh/images/example-kubernetes-deployment.png
  :alt: Example Kubernetes Deployment
  :align: center
  :width: 100%
  :class: img-bottom-margin


Trouble Shooting
------------------

Permissions and naming are the two most common causes of deployment problems. The Kubernetes Ingress
manifest below holds eleven names, made by either Terraform or Smarter, that have to agree.

.. figure:: https://cdn.smarter.sh/images/naming-example.png
  :alt: Example Kubernetes Ingress Manifest
  :align: center
  :width: 100%
  :class: img-bottom-margin

How resources are named
~~~~~~~~~~~~~~~~~~~~~~~

smarter-infrastructure and Smarter derive the names of a broad range of resources from the common
settings in Step 1. The names must agree, or the deployment fails. In these examples, the root
domain is ``example.com`` and the platform subdomain ``platform``.

.. list-table::
   :header-rows: 1
   :widths: 24 42 34

   * - Resource
     - Name
     - prod / alpha
   * - Kubernetes cluster
     - ``smarter-<subdomain>-ca-<UNIQUE_ID>``
     - one for every environment
   * - Kubernetes namespace
     - ``smarter-<subdomain>-<environment>``
     - ``smarter-platform-prod``
   * - Platform domain, and S3 bucket
     - ``<subdomain>.<root>``; ``<environment>.<subdomain>.<root>`` outside prod
     - ``platform.example.com`` / ``alpha.platform.example.com``
   * - API domain
     - ``api.<subdomain>.<root>``; ``<environment>.api.<subdomain>.<root>`` outside prod
     - ``api.platform.example.com`` / ``alpha.api.platform.example.com``
   * - CDN domain
     - ``cdn.<platform domain>``
     - ``cdn.platform.example.com``
   * - Backup and export buckets
     - ``backups.<platform domain>``, ``exports.<platform domain>``
     - ``backups.platform.example.com``
   * - IAM roles
     - ``<namespace>-smarter-irsa``, ``<namespace>-smarter-backup-irsa``
     - ``smarter-platform-prod-smarter-irsa``
   * - Database and its user
     - the namespace, with ``_`` for ``-``
     - ``smarter_platform_prod``

The ``ca`` in the cluster's name is fixed in smarter-infrastructure's ``aws/global.hcl``, whatever the
region.
