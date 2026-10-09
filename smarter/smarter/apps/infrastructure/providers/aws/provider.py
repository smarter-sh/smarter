"""
The AWS cloud provider.

:class:`AWSProvider` replaces ``smarter.common.helpers.aws_helpers.AWSInfrastructureConfig``. It
authenticates with AWS, with ``smarter_settings``' AWS credentials, and implements:

- DNS, with Route53: :class:`~smarter.apps.infrastructure.providers.aws.dns.Route53DNSService`.
- TLS certificates, with ACM:
  :class:`~smarter.apps.infrastructure.providers.aws.certificates.ACMCertificateService`.
- the Kubernetes cluster's kubeconfig, description, add-ons and node groups, with EKS.

Of the AWS services that the old helpers wrapped, only these are used by the platform. API
Gateway, DynamoDB, IAM, Lambda, RDS, Rekognition and S3 were not, and were removed.

In the unit tests, it refuses to reach AWS, unless ``allow_in_tests`` is True, because the
Smarter containers' AWS credentials are real.
"""

from typing import Any, Optional

import boto3

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ...const import CloudProviders, KubernetesResourceTypes
from ...exceptions import InfrastructureConfigurationError, SmarterInfrastructureError
from ...services.base import DiscoveredResource, refuse_in_unit_tests
from ..base import CloudProvider
from .certificates import ACMCertificateService
from .dns import Route53DNSService
from .helpers.base import AWSBase
from .helpers.eks import AWSEks

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])


class AWSProvider(CloudProvider):
    """
    Amazon Web Services.

    :param allow_in_tests: Allow it to reach AWS in the unit tests, e.g. in a test tagged
        :data:`~smarter.lib.unittest.runner.INFRASTRUCTURE`.
    """

    name = CloudProviders.AWS

    def __init__(self, allow_in_tests: bool = False, **kwargs):
        super().__init__(allow_in_tests=allow_in_tests, **kwargs)
        self._base: Optional[AWSBase] = None
        self._eks: Optional[AWSEks] = None
        self._dns: Optional[Route53DNSService] = None
        self._certificates: Optional[ACMCertificateService] = None

    def require_live(self) -> None:
        """
        Refuse to reach AWS from the unit tests, unless allowed.

        :raises InfrastructureConfigurationError: In the unit tests, unless allowed.
        """
        refuse_in_unit_tests("AWS", self.allow_in_tests)

    @property
    def base(self) -> AWSBase:
        """The low-level AWS helper that authenticates, created when it is first used."""
        self.require_live()
        if self._base is None:
            self._base = AWSBase()
        return self._base

    @property
    def session(self) -> Optional[boto3.Session]:
        """
        The boto3 session, for AWS-specific backends that need clients of their own.

        e.g. :class:`~smarter.apps.llmhost.services.nodegroups.EKSNodeGroupBackend`.
        """
        return self.base.aws_session

    @property
    def eks(self) -> AWSEks:
        """The low-level EKS helper."""
        self.require_live()
        if self._eks is None:
            self._eks = AWSEks()
        return self._eks

    @property
    def identity(self) -> Optional[dict[str, Any]]:
        try:
            return self.base.identity
        except InfrastructureConfigurationError:
            return None

    @property
    def ready(self) -> bool:
        try:
            self.require_live()
        except InfrastructureConfigurationError:
            return False
        try:
            identity = self.base.identity
        # pylint: disable=broad-except
        except Exception as e:
            return self.authentication_state(None, error=str(e))
        return self.authentication_state(identity, error="could not fetch the AWS identity")

    @property
    def account_id(self) -> Optional[str]:
        identity = self.identity
        return identity.get("Account") if isinstance(identity, dict) else None

    @property
    def sdk_version(self) -> str:
        return boto3.__version__

    @property
    def dns(self) -> Route53DNSService:
        if self._dns is None:
            self._dns = Route53DNSService(self)
        return self._dns

    @property
    def certificates(self) -> ACMCertificateService:
        if self._certificates is None:
            self._certificates = ACMCertificateService(self, self.dns)
        return self._certificates

    def update_kubeconfig(self) -> bool:
        if not self.ready:
            logger.warning("%s AWS is not ready, so the kubeconfig cannot be updated.", self.formatted_class_name)
            return False
        return self.eks.update_kubeconfig()

    def get_kubernetes_token(self) -> Optional[tuple[str, float]]:
        if not self.ready:
            return None
        try:
            return self.eks.get_token()
        # pylint: disable=broad-except
        except Exception as e:
            # kubectl falls back to the kubeconfig's aws eks get-token, which is slower but works.
            logger.warning("%s could not create an EKS token: %s", self.formatted_class_name, e)
            return None

    def get_kubernetes_cluster_info(self) -> dict[str, Any]:
        self.require_ready()
        with self.operation("get_kubernetes_cluster_info"):
            return self.eks.get_kubernetes_info()

    def get_kubernetes_cluster_resources(self) -> dict[str, list[DiscoveredResource]]:
        """
        Return the EKS cluster, which is billed by the hour, its add-ons, and its managed node groups.

        A node group is not billed: its nodes, EC2 instances, are, and the inventory finds them
        in the cluster. Nothing is returned if EKS cannot be described.
        """
        if not self.ready:
            return {}
        try:
            with self.operation("get_kubernetes_cluster_resources"):
                resources = self.eks.get_cluster_resources()
        except SmarterInfrastructureError as e:
            logger.warning("%s could not describe the EKS cluster's resources: %s", self.formatted_class_name, e)
            return {}
        return {
            str(resource_type): [
                DiscoveredResource(str(resource_type), item["name"], item["arn"], billable)
                for item in resources[key]
                if item["name"]
            ]
            for resource_type, key, billable in (
                (KubernetesResourceTypes.CLUSTER, "cluster", True),
                (KubernetesResourceTypes.ADDON, "addons", False),
                (KubernetesResourceTypes.NODEGROUP, "nodegroups", False),
            )
        }


__all__ = ["AWSProvider"]
