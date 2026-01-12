"""AWS EKS helper class."""

import logging

from smarter.common.conf import smarter_settings

from .aws import AWSBase


logger = logging.getLogger(__name__)


class AWSEks(AWSBase):
    """
    AWS EKS helper class. Provides a high-level interface for interacting
    with Amazon Elastic Kubernetes Service (EKS) clusters.

    This helper class abstracts common operations related to AWS EKS, such as retrieving cluster information and
    managing connections to EKS resources. It simplifies the process of communicating with the AWS EKS API by
    encapsulating client initialization and error handling, making it easier to integrate EKS management into
    automation workflows or larger AWS orchestration systems.

    The class is designed to work with application configuration settings and ensures that AWS sessions are
    properly initialized before performing any operations. It provides logging and exception handling to support
    robust and maintainable code when working with Kubernetes clusters hosted on AWS.
    """

    _client = None
    _client_type: str = "eks"

    def get_kubernetes_info(self) -> dict:
        """
        Return the Kubernetes cluster information.

        :return: Kubernetes cluster information
        :rtype: dict
        """
        logger.debug("%s.get_kubernetes_info() called", self.formatted_class_name)
        response = self.client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)
        response = response["cluster"]
        retval = {
            "health": response.get("health"),
            "platformVersion": response.get("platformVersion"),
            "status": response.get("status"),
            "version": response.get("version"),
        }
        return retval
