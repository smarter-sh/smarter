"""
The AWS cloud provider: Route53, Certificate Manager, and EKS.

The platform does not import this package: it uses :mod:`smarter.apps.infrastructure.services`,
which uses this provider when ``smarter_settings.cloud_provider`` is ``aws``, the default.
"""

from .provider import AWSProvider

__all__ = ["AWSProvider"]
