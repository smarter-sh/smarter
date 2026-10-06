"""
The low-level AWS EKS helper.

It describes the platform's EKS cluster, and writes its kubeconfig, for
:class:`~smarter.apps.infrastructure.providers.aws.AWSProvider`.
"""

import subprocess
from typing import Any

from smarter.common.conf import smarter_settings
from smarter.lib import logging

from .base import AWSBase
from .exceptions import AWSNotReadyError

logger = logging.getLogger(__name__)


class AWSEks(AWSBase):
    """The AWS EKS helper: the platform's cluster, ``smarter_settings.aws_eks_cluster_name``."""

    _client = None
    _client_type: str = "eks"

    def get_kubernetes_info(self) -> dict[str, Any]:
        """
        Describe the platform's EKS cluster.

        :returns: The cluster's health, platformVersion, status and Kubernetes version.
        """
        logger.debug("%s.get_kubernetes_info() called", self.formatted_class_name)
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS EKS.")
        response = self.client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)["cluster"]
        return {
            "health": response.get("health"),
            "platformVersion": response.get("platformVersion"),
            "status": response.get("status"),
            "version": response.get("version"),
        }

    def update_kubeconfig(self) -> bool:
        """
        Write the kubeconfig of the platform's EKS cluster, with ``aws eks update-kubeconfig``.

        :returns: True if it was written.
        """
        cluster_name = smarter_settings.aws_eks_cluster_name
        region = smarter_settings.aws_region
        if not cluster_name or not region:
            logger.error(
                "%s.update_kubeconfig() aws_eks_cluster_name and aws_region must be set to update the kubeconfig.",
                self.formatted_class_name,
            )
            return False
        command = ["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster_name]
        try:
            subprocess.check_call(command)  # nosec B603 B607
        except (subprocess.CalledProcessError, OSError) as e:
            logger.error("%s.update_kubeconfig() failed to update the kubeconfig: %s", self.formatted_class_name, e)
            return False
        logger.debug("%s.update_kubeconfig() updated the kubeconfig of %s", self.formatted_class_name, cluster_name)
        return True


__all__ = ["AWSEks"]
