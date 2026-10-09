"""
The low-level AWS EKS helper.

It describes the platform's EKS cluster, its add-ons and node groups, and writes its kubeconfig, for
:class:`~smarter.apps.infrastructure.providers.aws.AWSProvider`.
"""

import base64
import subprocess
import time
from typing import Any

from botocore.signers import RequestSigner

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_banner
from smarter.lib import logging

from .base import AWSBase
from .exceptions import AWSNotReadyError

logger = logging.getLogger(__name__)

EKS_TOKEN_PREFIX = "k8s-aws-v1."
EKS_TOKEN_CLUSTER_HEADER = "x-k8s-aws-id"
EKS_TOKEN_LIFETIME_SECONDS = 600
"""
How long an EKS token is used.

EKS accepts one for 15 minutes, and ``aws eks get-token`` reports
14, so 10 leaves a margin for the clocks of the cluster and the worker.
"""


class AWSEks(AWSBase):
    """
    The AWS EKS helper: the platform's cluster, ``smarter_settings.aws_eks_cluster_name``.

    The cluster is optional. Without its name, the platform runs, but nothing is deployed to
    Kubernetes, and the first attempt to reach the cluster logs how to set it.
    """

    _client = None
    _client_type: str = "eks"
    _cluster_name_warned: bool = False
    """Whether the missing cluster name was logged.

    Shared by every instance, so that it is logged once.
    """

    def cluster_name_is_set(self) -> bool:
        """
        Return True if ``smarter_settings.aws_eks_cluster_name`` is set.

        If it is not, log how to set it, once per process.
        """
        if smarter_settings.aws_eks_cluster_name:
            return True
        if not AWSEks._cluster_name_warned:
            AWSEks._cluster_name_warned = True
            logger.error(
                formatted_banner(
                    "[KUBERNETES DISABLED] SMARTER_AWS_EKS_CLUSTER_NAME is not set.",
                    "The platform runs without it, but LLMClients and LLMHosts are not deployed to Kubernetes.",
                    "To deploy them, add the name of your AWS EKS cluster to .env, and restart the platform:",
                    "",
                    "    SMARTER_AWS_EKS_CLUSTER_NAME=<your EKS cluster>",
                    "",
                    "The AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION) must be able to",
                    "describe the cluster. See https://github.com/smarter-sh/smarter-infrastructure",
                )
            )
        return False

    def get_kubernetes_info(self) -> dict[str, Any]:
        """
        Describe the platform's EKS cluster.

        :returns: The cluster's health, platformVersion, status and Kubernetes version.
        """
        logger.debug("%s.get_kubernetes_info() called", self.formatted_class_name)
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS EKS.")
        if not self.cluster_name_is_set():
            raise AWSNotReadyError(f"{self.formatted_class_name} aws_eks_cluster_name is not set.")
        response = self.client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)["cluster"]
        return {
            "health": response.get("health"),
            "platformVersion": response.get("platformVersion"),
            "status": response.get("status"),
            "version": response.get("version"),
        }

    def get_cluster_resources(self) -> dict[str, list[dict[str, str]]]:
        """
        Describe the cloud resources of the platform's EKS cluster: the cluster, its add-ons and its node groups.

        :returns: The ``name`` and ``arn`` of each, by ``cluster``, ``addons`` and ``nodegroups``.
        :raises AWSNotReadyError: If AWS is not ready, or the cluster's name is not set.
        """
        logger.debug("%s.get_cluster_resources() called", self.formatted_class_name)
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS EKS.")
        if not self.cluster_name_is_set():
            raise AWSNotReadyError(f"{self.formatted_class_name} aws_eks_cluster_name is not set.")
        cluster_name = smarter_settings.aws_eks_cluster_name
        cluster = self.client.describe_cluster(name=cluster_name)["cluster"]
        addons = [
            self.client.describe_addon(clusterName=cluster_name, addonName=name)["addon"]
            for page in self.client.get_paginator("list_addons").paginate(clusterName=cluster_name)
            for name in page.get("addons", [])
        ]
        nodegroups = [
            self.client.describe_nodegroup(clusterName=cluster_name, nodegroupName=name)["nodegroup"]
            for page in self.client.get_paginator("list_nodegroups").paginate(clusterName=cluster_name)
            for name in page.get("nodegroups", [])
        ]
        return {
            "cluster": [{"name": cluster.get("name", cluster_name), "arn": cluster.get("arn", "")}],
            "addons": [{"name": addon.get("addonName", ""), "arn": addon.get("addonArn", "")} for addon in addons],
            "nodegroups": [
                {"name": nodegroup.get("nodegroupName", ""), "arn": nodegroup.get("nodegroupArn", "")}
                for nodegroup in nodegroups
            ],
        }

    def update_kubeconfig(self) -> bool:
        """
        Write the kubeconfig of the platform's EKS cluster, with ``aws eks update-kubeconfig``.

        :returns: True if it was written.
        """
        if not self.cluster_name_is_set():
            return False
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

    def get_token(self) -> tuple[str, float]:
        """
        Create a bearer token for the platform's EKS cluster, as ``aws eks get-token`` does.

        The token is an STS GetCallerIdentity url, presigned with the session's credentials and the
        cluster's name, which EKS calls to identify the caller. Creating it makes no request, so it
        takes milliseconds rather than the seconds that the aws cli takes to start.

        :returns: The token, and when it should no longer be used, as a :func:`time.time`.
        :raises AWSNotReadyError: If AWS is not ready, or the cluster's name or region is not set.
        """
        cluster_name = smarter_settings.aws_eks_cluster_name
        region = self.aws_region
        if not self.ready or not self.aws_session or not cluster_name or not region:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to create an EKS token.")
        sts = self.aws_session.client("sts", region_name=region)
        signer = RequestSigner(
            sts.meta.service_model.service_id,
            region,
            "sts",
            "v4",
            self.aws_session.get_credentials(),
            self.aws_session.events,
        )
        url = signer.generate_presigned_url(
            {
                "method": "GET",
                "url": f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
                "body": {},
                "headers": {EKS_TOKEN_CLUSTER_HEADER: cluster_name},
                "context": {},
            },
            region_name=region,
            expires_in=60,
            operation_name="",
        )
        token = EKS_TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").rstrip("=")
        return token, time.time() + EKS_TOKEN_LIFETIME_SECONDS


__all__ = ["AWSEks"]
