"""
The low-level AWS helpers: thin wrappers of the boto3 clients that Smarter uses.

Only :class:`~smarter.apps.infrastructure.providers.aws.AWSProvider` and its services use them.
The platform uses the infrastructure services, :mod:`smarter.apps.infrastructure.services`.

- :class:`~.base.AWSBase`: authentication, the boto3 session, and the account's identity.
- :class:`~.route53.AWSRoute53`: hosted zones and record sets.
- :class:`~.acm.AWSCertificateManager`: DNS-validated public certificates.
- :class:`~.eks.AWSEks`: the platform's EKS cluster, and its kubeconfig.
"""
