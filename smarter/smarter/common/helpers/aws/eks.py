"""AWS EKS helper class."""

from smarter.common.conf import settings as smarter_settings

from .aws import AWSBase, SmarterAWSException


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

    @property
    def client(self):
        """
        Return the AWS EKS client.

        :return: boto3 EKS client
        :rtype: boto3.client
        """
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("eks")
        return self._client

    def get_kubernetes_info(self) -> dict:
        """
        Return the Kubernetes cluster information.

        :return: Kubernetes cluster information
        :rtype: dict
        """
        response = self.client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)
        response = response["cluster"]
        retval = {
            "health": response.get("health"),
            "platformVersion": response.get("platformVersion"),
            "status": response.get("status"),
            "version": response.get("version"),
        }
        return retval
