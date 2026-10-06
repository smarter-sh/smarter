AWS Provider Overview
=====================

Smarter uses these AWS services:

- **Route53**, for DNS: the zones and records of the platform's domains, of LLMClients' hosts,
  and of customers' custom domains.
- **AWS Certificate Manager (ACM)**, for the TLS certificates of custom domains.
- **EKS**, the Kubernetes cluster that Smarter runs on, and the node groups of self-hosted LLMs.
- **Simple Email Service (SES)**, as the SMTP server of the platform's email.

The platform does not call these services directly. It uses the
:doc:`infrastructure services <../infrastructure>`, which the AWS provider,
:class:`~smarter.apps.infrastructure.providers.aws.provider.AWSProvider`, implements when
``SMARTER_CLOUD_PROVIDER`` is ``aws``, the default:

.. code-block:: python

   from smarter.apps.infrastructure.services import infrastructure

   zone, created = infrastructure.dns.get_or_create_zone("example.com")
   print(zone.id, zone.name_servers)

The AWS provider is built on low-level helpers, one per AWS service, which wrap the boto3
clients. Only the AWS provider uses them:

- :class:`~smarter.apps.infrastructure.providers.aws.helpers.base.AWSBase` authenticates with
  AWS, with an IAM role inside AWS, an AWS profile, or an access key pair, and gives the boto3
  session and the account's identity.
- :class:`~smarter.apps.infrastructure.providers.aws.helpers.route53.AWSRoute53` manages
  hosted zones and their record sets.
- :class:`~smarter.apps.infrastructure.providers.aws.helpers.acm.AWSCertificateManager`
  requests, describes and deletes DNS-validated certificates.
- :class:`~smarter.apps.infrastructure.providers.aws.helpers.eks.AWSEks` describes the EKS
  cluster, and writes its kubeconfig.
