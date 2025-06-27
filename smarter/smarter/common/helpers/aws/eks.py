"""AWS EKS helper class."""

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError

from .aws import AWSBase


class AWSEks(AWSBase):
    """AWS EKS helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS DynamoDB client."""
        if not self.aws_session:
            raise SmarterConfigurationError("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("eks")
        return self._client

    def get_kubernetes_info(self):
        """Return the version of the MySQL server"""
        response = self.client.describe_cluster(name=smarter_settings.aws_eks_cluster_name)
        response = response["cluster"]
        retval = {
            "health": response.get("health"),
            "platformVersion": response.get("platformVersion"),
            "status": response.get("status"),
            "version": response.get("version"),
        }
        return retval
