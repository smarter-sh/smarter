"""AWS RDS helper class."""

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError

from .aws import AWSBase


class AWSRds(AWSBase):
    """AWS RDS helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS DynamoDB client."""
        if not self.aws_session:
            raise SmarterConfigurationError("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("rds")
        return self._client

    def get_mysql_info(self):
        """Return the version of the MySQL server"""
        response = self.client.describe_db_instances(DBInstanceIdentifier=smarter_settings.aws_db_instance_identifier)
        response = response["DBInstances"][0]
        retval = {
            "Engine": response.get("Engine"),
            "EngineVersion": response.get("EngineVersion"),
        }
        return retval
