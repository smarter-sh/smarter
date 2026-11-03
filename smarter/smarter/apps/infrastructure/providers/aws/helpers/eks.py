"""
The low-level AWS EKS helper.

It describes the platform's EKS cluster, its add-ons and node groups, and writes its kubeconfig, for
:class:`~smarter.apps.infrastructure.providers.aws.AWSProvider`.
"""

import base64
import subprocess
import time
from typing import Any, Optional

from botocore.exceptions import ClientError
from botocore.signers import RequestSigner

from smarter.apps.infrastructure.cluster_health import (
    AddonHealth,
    ClusterHealth,
    ClusterInsight,
    HealthIssue,
    NodeGroupHealth,
    version_key,
)
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.typing import SmarterDictType

from .base import AWSBase
from .exceptions import AWSNotReadyError, SmarterAWSError

logger = logging.getLogger(__name__)

EKS_TOKEN_PREFIX = "k8s-aws-v1."
EKS_TOKEN_CLUSTER_HEADER = "x-k8s-aws-id"
EKS_TOKEN_LIFETIME_SECONDS = 600
"""
How long an EKS token is used.

EKS accepts one for 15 minutes, and ``aws eks get-token`` reports
14, so 10 leaves a margin for the clocks of the cluster and the worker.
"""


def health_issues(resource: SmarterDictType) -> tuple[HealthIssue, ...]:
    """
    Read the health issues of an EKS cluster, node group or add-on from its description.

    EKS describes each of them with a ``health`` object, whose ``issues`` each have a ``code``, a
    ``message`` and the ``resourceIds`` that they affect. A resource without issues has an empty list,
    or no ``health`` at all.

    :param resource: The description, e.g. ``describe_nodegroup(...)["nodegroup"]``.
    :returns: The issues, in EKS's order, or an empty tuple if there are none.
    """
    health = resource.get("health") or {}
    issues = []
    for issue in health.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        resource_ids = issue.get("resourceIds") or []
        issues.append(
            HealthIssue(
                code=str(issue.get("code", "")),
                message=str(issue.get("message", "")),
                resources=tuple(str(resource_id) for resource_id in resource_ids),
            )
        )
    return tuple(issues)


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

    @property
    def eks(self):
        """
        The boto3 EKS client.

        :raises AWSNotReadyError: If AWS is not ready.
        """
        client = self.client
        if not self.ready or not client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS EKS.")
        return client

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
                SmarterFormattedText.banner(
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

    def get_kubernetes_info(self) -> SmarterDictType:
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
        addon_pages = self.client.get_paginator("list_addons").paginate(clusterName=cluster_name)
        addons = []
        for page in addon_pages:
            for name in page.get("addons", []):
                response = self.client.describe_addon(clusterName=cluster_name, addonName=name)
                addons.append(response["addon"])
        nodegroup_pages = self.client.get_paginator("list_nodegroups").paginate(clusterName=cluster_name)
        nodegroups = []
        for page in nodegroup_pages:
            for name in page.get("nodegroups", []):
                response = self.client.describe_nodegroup(clusterName=cluster_name, nodegroupName=name)
                nodegroups.append(response["nodegroup"])
        cluster_items = [{"name": cluster.get("name", cluster_name), "arn": cluster.get("arn", "")}]
        addon_items = [{"name": addon.get("addonName", ""), "arn": addon.get("addonArn", "")} for addon in addons]
        nodegroup_items = [
            {"name": nodegroup.get("nodegroupName", ""), "arn": nodegroup.get("nodegroupArn", "")}
            for nodegroup in nodegroups
        ]
        resources = {
            "cluster": cluster_items,
            "addons": addon_items,
            "nodegroups": nodegroup_items,
        }
        return resources

    def get_cluster_health(self) -> ClusterHealth:
        """
        Describe the health of the platform's EKS cluster, ``smarter_settings.aws_eks_cluster_name``.

        It reads the control plane, each managed node group, each add-on with its newest version for the
        cluster's Kubernetes version, and EKS's insights, e.g. the cluster's readiness for the next
        Kubernetes version. The node groups, the add-ons and the insights are each read on their own: a
        part that fails, e.g. because the credentials may not call ``eks:ListInsights``, is named in
        :attr:`ClusterHealth.errors`, with AWS's error code, and the other parts are still returned.

        Side effects: read-only calls to the EKS api: ``DescribeCluster``, ``ListNodegroups`` and
        ``DescribeNodegroup``, ``ListAddons``, ``DescribeAddon`` and ``DescribeAddonVersions``, and
        ``ListInsights``. Nothing is changed.

        :returns: The cluster's health.
        :raises AWSNotReadyError: If AWS is not ready, or the cluster's name is not set.
        :raises botocore.exceptions.ClientError: If the cluster itself cannot be described.
        """
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS EKS.")
        if not self.cluster_name_is_set():
            raise AWSNotReadyError(f"{self.formatted_class_name} aws_eks_cluster_name is not set.")
        cluster_name = smarter_settings.aws_eks_cluster_name
        if not cluster_name:
            raise AWSNotReadyError(f"{self.formatted_class_name} aws_eks_cluster_name is not set.")
        cluster = self.client.describe_cluster(name=cluster_name)["cluster"]
        health = ClusterHealth(
            name=str(cluster.get("name", cluster_name)),
            status=str(cluster.get("status", "")),
            version=str(cluster.get("version", "")),
            platform_version=str(cluster.get("platformVersion", "")),
            issues=health_issues(cluster),
        )

        try:
            health.nodegroups = self._nodegroups(cluster_name)
        except ClientError as e:
            health.errors.append(self._part_error("nodegroups", e))
        try:
            health.addons = self._addons(cluster_name, health.version)
        except ClientError as e:
            health.errors.append(self._part_error("addons", e))
        try:
            health.insights = self._insights(cluster_name)
        except ClientError as e:
            health.errors.append(self._part_error("insights", e))
        return health

    def _part_error(self, part: str, error: ClientError) -> str:
        """
        Describe a part of the cluster's health that could not be read, and log it.

        :param part: The part, e.g. ``insights``.
        :param error: AWS's error.
        :returns: The part and AWS's error code, e.g. ``insights: AccessDeniedException``.
        """
        details = error.response.get("Error", {})
        code = details.get("Code", "ClientError")
        logger.warning("%s.get_cluster_health() could not read %s: %s", self.formatted_class_name, part, code)
        return f"{part}: {code}"

    def _nodegroups(self, cluster_name: str) -> list[NodeGroupHealth]:
        """
        Describe each managed node group of the cluster.

        Side effects: one ``ListNodegroups`` call per page of node groups, and one ``DescribeNodegroup``
        call per node group.

        :param cluster_name: The cluster's name.
        :returns: Each node group's health, in EKS's order.
        :raises botocore.exceptions.ClientError: If the node groups cannot be listed or described.
        """
        nodegroups = []
        paginator = self.eks.get_paginator("list_nodegroups")
        for page in paginator.paginate(clusterName=cluster_name):
            for name in page.get("nodegroups", []):
                response = self.eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=name)
                nodegroup = response["nodegroup"]
                scaling = nodegroup.get("scalingConfig") or {}
                instance_types = nodegroup.get("instanceTypes") or []
                health = NodeGroupHealth(
                    name=str(nodegroup.get("nodegroupName", name)),
                    status=str(nodegroup.get("status", "")),
                    desired_size=scaling.get("desiredSize"),
                    min_size=scaling.get("minSize"),
                    max_size=scaling.get("maxSize"),
                    instance_types=tuple(instance_types),
                    capacity_type=str(nodegroup.get("capacityType", "")),
                    release_version=str(nodegroup.get("releaseVersion", "")),
                    issues=health_issues(nodegroup),
                )
                nodegroups.append(health)
        return nodegroups

    def _addons(self, cluster_name: str, kubernetes_version: str) -> list[AddonHealth]:
        """
        Describe each add-on of the cluster, with its newest version for the cluster's Kubernetes version.

        Side effects: one ``ListAddons`` call per page of add-ons, and one ``DescribeAddon`` and one
        ``DescribeAddonVersions`` call per add-on.

        :param cluster_name: The cluster's name.
        :param kubernetes_version: The cluster's Kubernetes version, e.g. ``1.33``, for which the newest
            add-on versions are looked up.
        :returns: Each add-on's health, in EKS's order.
        :raises botocore.exceptions.ClientError: If the add-ons cannot be listed or described.
        """
        addons = []
        paginator = self.eks.get_paginator("list_addons")
        for page in paginator.paginate(clusterName=cluster_name):
            for name in page.get("addons", []):
                response = self.eks.describe_addon(clusterName=cluster_name, addonName=name)
                addon = response["addon"]
                health = AddonHealth(
                    name=str(addon.get("addonName", name)),
                    version=str(addon.get("addonVersion", "")),
                    status=str(addon.get("status", "")),
                    latest_version=self._latest_addon_version(name, kubernetes_version),
                    issues=health_issues(addon),
                )
                addons.append(health)
        return addons

    def _latest_addon_version(self, name: str, kubernetes_version: str) -> Optional[str]:
        """
        Find the newest version of an add-on that EKS offers for a Kubernetes version.

        EKS lists the versions without promising an order, so they are compared by their numbers (see
        :func:`~smarter.apps.infrastructure.cluster_health.version_key`).

        Side effects: one ``DescribeAddonVersions`` call.

        :param name: The add-on's name, e.g. ``coredns``.
        :param kubernetes_version: The Kubernetes version, e.g. ``1.33``.
        :returns: The newest version, e.g. ``v1.11.4-eksbuild.2``, or None if EKS offers none, or the
            versions could not be read, e.g. without the ``eks:DescribeAddonVersions`` permission. The
            failure is logged, and does not fail the add-on's description.
        """
        try:
            response = self.eks.describe_addon_versions(addonName=name, kubernetesVersion=kubernetes_version)
        except ClientError as e:
            logger.debug("%s could not read the versions of %s: %s", self.formatted_class_name, name, e)
            return None
        versions = []
        for addon in response.get("addons", []):
            for version in addon.get("addonVersions", []):
                versions.append(str(version.get("addonVersion", "")))
        if not versions:
            return None
        return max(versions, key=version_key)

    def _insights(self, cluster_name: str) -> list[ClusterInsight]:
        """
        Read EKS's insights about the cluster, e.g. its readiness for the next Kubernetes version.

        Side effects: one ``ListInsights`` call per page of insights.

        :param cluster_name: The cluster's name.
        :returns: Each insight, in EKS's order.
        :raises botocore.exceptions.ClientError: If the insights cannot be listed, e.g. without the
            ``eks:ListInsights`` permission.
        """
        insights = []
        arguments: SmarterDictType = {"clusterName": cluster_name}
        while True:
            response = self.eks.list_insights(**arguments)
            for insight in response.get("insights", []):
                status = insight.get("insightStatus") or {}
                result = ClusterInsight(
                    name=str(insight.get("name", "")),
                    category=str(insight.get("category", "")),
                    status=str(status.get("status", "")),
                    reason=str(status.get("reason", "")),
                    kubernetes_version=str(insight.get("kubernetesVersion", "")),
                )
                insights.append(result)
            next_token = response.get("nextToken")
            if not next_token:
                return insights
            arguments["nextToken"] = next_token

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
            # The aws cli prints "Added new context <cluster arn>", and the arn holds the AWS
            # account id, which the rest of the log masks. Errors still go to stderr.
            subprocess.check_call(command, stdout=subprocess.DEVNULL)  # nosec B603 B607
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
        if url is None:
            raise SmarterAWSError(f"{self.formatted_class_name} could not presign the EKS token url.")
        token = EKS_TOKEN_PREFIX + base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8").rstrip("=")
        return token, time.time() + EKS_TOKEN_LIFETIME_SECONDS


__all__ = ["AWSEks"]
