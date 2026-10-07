"""
Smarter's infrastructure services: DNS, TLS certificates, Kubernetes, and email.

The platform reaches its infrastructure only through this app's service layer,
:mod:`smarter.apps.infrastructure.services`, never through a cloud provider's SDK. Each cloud
provider, e.g. AWS, implements the cloud-specific services in a package of
:mod:`smarter.apps.infrastructure.providers`. Kubernetes (kubectl) and email (SMTP) do not
depend on a cloud, so they are implemented once, for every provider.
"""
