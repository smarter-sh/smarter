Infrastructure Services
=======================

Overview
--------

Smarter creates and manages cloud infrastructure on behalf of its users. Deploying an
:doc:`LLMClient <../../smarter-resources/smarter-llmclient>` creates a DNS record for its
host, and a Kubernetes Ingress whose TLS certificate is issued automatically. Registering a
:doc:`custom domain <../../smarter-resources/smarter-custom-domain>` creates a DNS zone and a
TLS certificate. A self-hosted :doc:`vectorstore <../../smarter-resources/smarter-vectorstore>`
runs in Kubernetes, with a persistent volume for its data. And the platform sends email, for
example to activate an account or to reset a password.

All of this is done through one layer of Python code, the **infrastructure services**, in the
Django app ``smarter.apps.infrastructure``. The rest of the platform never calls a cloud
provider's SDK, such as AWS's boto3. It asks the infrastructure services for what it needs, in
terms that do not depend on the cloud: a DNS zone, a DNS record, a TLS certificate, a
Kubernetes manifest, an email.

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    zone, created = infrastructure.dns.get_or_create_zone("example.com")
    certificate_id, _ = infrastructure.certificates.get_or_create_certificate("example.com")
    infrastructure.certificates.create_validation_records(certificate_id)
    infrastructure.kubernetes.apply_manifest(manifest)
    infrastructure.email.send_email(subject="Welcome!", body="<p>Hello</p>", to="user@example.com", html=True)

Smarter runs on :doc:`Amazon Web Services <aws>` today. Because the platform depends only on
the infrastructure services, supporting another cloud, such as Microsoft Azure, Google Cloud
or DigitalOcean, means adding a cloud provider, not changing the platform.

The Services
------------

``infrastructure`` gives the platform five services:

- ``dns``: DNS zones and records. A zone, for example an AWS Route53 hosted zone, holds the
  records of a domain and its subdomains. Zones and records are described by the
  provider-independent :class:`~smarter.apps.infrastructure.services.dns.DNSZone` and
  :class:`~smarter.apps.infrastructure.services.dns.DNSRecord`.
- ``certificates``: TLS certificates, issued by the cloud provider, for a domain and its
  subdomains. The provider issues a certificate once DNS records prove that the domain is
  under Smarter's control, so the certificate service creates those validation records with
  the DNS service.
- ``kubernetes``: the resources of the platform's Kubernetes cluster, through
  `kubectl <https://kubernetes.io/docs/reference/kubectl/>`__.
- ``email``: the platform's outgoing email, through SMTP. See :doc:`smtp`.
- ``provider``: the cloud provider itself, for example its account identity, and a
  description of the Kubernetes cluster for the ``status`` API.

Each service has a ``ready`` property, which is ``True`` once it is authenticated and
connected. Celery tasks that create infrastructure check it first, so that a Smarter
installation without cloud credentials, such as a developer's laptop, skips them rather than
failing.

Cloud Providers
---------------

Some services depend on a cloud, and some do not:

- **DNS and TLS certificates** are implemented by each cloud provider. On AWS, DNS is Route53,
  and certificates come from AWS Certificate Manager (ACM).
- **Kubernetes** does not depend on a cloud: only the cluster's credentials do. kubectl works
  the same with any cluster, so the Kubernetes service is implemented once, and the cloud
  provider contributes only the kubeconfig, for example with ``aws eks update-kubeconfig``.
- **Email** does not depend on a cloud either. Smarter sends it with SMTP, to any SMTP server,
  for example AWS Simple Email Service's.

``SMARTER_CLOUD_PROVIDER``, which is ``smarter_settings.cloud_provider``, selects the provider.
It is ``aws`` by default. ``memory`` selects a provider that keeps DNS zones, records and
certificates in memory, for local development without a cloud account, and for the unit tests.

.. code-block:: bash

    SMARTER_CLOUD_PROVIDER=aws

A provider implements only a few primitives of the DNS and certificate services, for example
"find a zone", "create a zone", "list a zone's records". The operations that the platform
uses, for example copying the environment's A record to a new LLMClient's host, are built on
those primitives once, in the services, so they behave the same in every cloud.

Adding a Cloud
~~~~~~~~~~~~~~

To add a cloud, for example Azure:

1. Add a package, ``smarter.apps.infrastructure.providers.azure``, with a subclass of
   :class:`~smarter.apps.infrastructure.providers.base.CloudProvider`, and subclasses of
   :class:`~smarter.apps.infrastructure.services.dns.DNSService` and
   :class:`~smarter.apps.infrastructure.services.certificates.CertificateService` that implement
   their abstract primitives with the cloud's SDK. Translate the SDK's errors into the
   infrastructure exceptions, with the services' ``operation()`` context manager.
2. Register the provider in :mod:`smarter.apps.infrastructure.providers`, under its
   :class:`~smarter.apps.infrastructure.const.CloudProviders` name.
3. Set ``SMARTER_CLOUD_PROVIDER=azure``.

The AWS provider, :mod:`smarter.apps.infrastructure.providers.aws`, and the in-memory provider,
:mod:`smarter.apps.infrastructure.providers.memory`, are examples.

Signals
-------

The infrastructure services send Django signals, whichever provider implements them, so that
the platform can observe its infrastructure without knowing which cloud it runs on. Each signal
has the arguments ``service``, for example ``dns``, and ``provider``, for example ``aws``.

- ``infrastructure_authenticated`` and ``infrastructure_authentication_failed``: a provider
  authenticated with its cloud, or could not. They are sent when the state changes, rather than
  on every check.
- ``infrastructure_connected`` and ``infrastructure_connection_failed``: a service connected to
  its backend, for example the Kubernetes cluster, or could not.
- ``billable_resource_creating``, ``billable_resource_created``,
  ``billable_resource_destroying`` and ``billable_resource_destroyed``: a resource that the
  cloud bills for, for example a DNS zone, a persistent volume, or a load balancer, is about to
  be, or was, created or destroyed.
- ``resource_created`` and ``resource_destroyed``: a resource that is not billed on its own,
  for example a DNS record or a free TLS certificate, was created, updated or destroyed.
- ``resource_applied``: a Kubernetes manifest was applied.
- ``infrastructure_operation_failed``: a service's operation failed.
- ``email_sent`` and ``email_failed``.

Connect a receiver to observe them:

.. code-block:: python

    from django.dispatch import receiver
    from smarter.apps.infrastructure.signals import billable_resource_created

    @receiver(billable_resource_created)
    def meter(sender, service, provider, resource_type, resource_name, resource_id, **kwargs):
        ...

The Resource Ledger
-------------------

Smarter's own receivers log every infrastructure signal, and record each resource that is
created or destroyed in a ledger, the Django model
:class:`~smarter.apps.infrastructure.models.InfrastructureResource`: its provider, service,
type, name, the provider's id for it, whether it is billable, and whether it still exists. The
ledger answers "what has Smarter provisioned in our cloud account, and what is it costing us?"
without asking each cloud.

Much of the infrastructure that Smarter runs on isn't created by the platform: the Kubernetes
cluster, its add-ons and its node groups are provisioned with Terraform, nodes come and go with
the cluster's autoscaler, and cert-manager issues the TLS certificates of the ingresses. The
inventory, :mod:`smarter.apps.infrastructure.services.inventory`, discovers them, and reconciles
the ledger with what exists. The cluster is shared by every environment, so besides the cluster
itself, that is, the cluster, its add-ons, node groups and nodes, it discovers only the
resources of the environment's namespace, ``smarter_settings.environment_namespace``. It records these resource types:

- ``kubernetes.cluster``: the managed cluster, for example AWS EKS, which is billed by the hour.
- ``kubernetes.addon``: the cluster's managed add-ons, for example the VPC CNI, CoreDNS and the
  EBS CSI driver.
- ``kubernetes.nodegroup``: the managed node groups. Their nodes are billed, not the groups.
- ``kubernetes.node``: the compute nodes, for example EC2 instances. Billable.
- ``kubernetes.persistentvolume``: the block storage volumes, for example EBS volumes, that are
  bound to claims in the environment's namespace. Billable.
- ``kubernetes.loadbalancer``: the environment's Services of type LoadBalancer, which provision
  cloud load balancers. Billable.
- ``kubernetes.ingress`` and ``kubernetes.certificate``: the environment's Ingresses and
  cert-manager Certificates.

A resource that the ledger doesn't know is recorded as created, and an active one that no
longer exists as destroyed, with the same signals as the services send, so the ledger is still
written only by its receivers. A resource type that can't be listed, for example because the
cluster is unavailable, is left as it is. The inventory only reads the cloud: it never creates
or destroys anything. Celery Beat runs it every 15 minutes, with the task
``smarter.apps.infrastructure.tasks.sync_infrastructure_inventory``, on the infrastructure queue.
To run it on demand:

.. code-block:: bash

    python manage.py sync_infrastructure_inventory

Superusers see the ledger in the web console, under **Settings, Infrastructure Resources**: a
summary of the active, billable and destroyed resources, and a list that can be filtered by
status, by provider, by whether a resource is billable, and by text. The list is read-only: the
platform writes the ledger as it creates, destroys and discovers resources. It is also in the
Django admin.

Testing Safely
--------------

The Smarter Docker containers hold real cloud credentials, and a real kubeconfig, which can
create billable resources. So the real services refuse to reach their backends from the unit
tests: the AWS provider is never ready, kubectl never runs, and SMTP sends nothing. Tests
install fakes instead:

.. code-block:: python

    from smarter.apps.infrastructure.providers import configure_provider
    from smarter.apps.infrastructure.providers.memory import InMemoryProvider
    from smarter.apps.infrastructure.services import InMemoryEmailService, configure_email

    provider = InMemoryProvider()
    configure_provider(lambda: provider)
    configure_email(InMemoryEmailService)
    ...
    configure_provider(None)
    configure_email(None)

Tests of code that uses ``infrastructure`` can also patch it where it is used, for example
``patch("smarter.apps.llmclient.tasks.verify_custom_domain.infrastructure")``. Tests that must
use real infrastructure are tagged ``infrastructure``, are skipped by default, and allow it
explicitly, for example with ``AWSProvider(allow_in_tests=True)``.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   infrastructure/services
   infrastructure/dns
   infrastructure/certificates
   infrastructure/kubernetes
   infrastructure/email
   infrastructure/inventory
   infrastructure/providers
   infrastructure/aws
   infrastructure/memory
   infrastructure/signals
   infrastructure/models
   infrastructure/views
   infrastructure/exceptions
   infrastructure/const
