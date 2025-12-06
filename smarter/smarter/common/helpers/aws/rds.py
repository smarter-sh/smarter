"""AWS RDS helper class."""

from smarter.common.conf import settings as smarter_settings

from .aws import AWSBase, SmarterAWSException


class AWSRds(AWSBase):
    """
    AWS RDS helper class. Provides a high-level interface for managing
    Amazon Relational Database Service (RDS) resources.

    This helper class abstracts common operations related to AWS RDS, such as retrieving information about database
    instances and managing connections to the RDS service. It simplifies interactions with the AWS RDS API by
    encapsulating client initialization and error handling, making it easier to integrate RDS management into
    automation workflows or larger AWS orchestration systems.

    The class is designed to work with application configuration settings and ensures that AWS sessions are properly
    initialized before performing any operations. It supports robust and maintainable code by providing logging and
    exception handling for operations involving RDS resources, such as database instances, within AWS environments.
    """

    _client = None

    @property
    def client(self):
        """
        Return the AWS DynamoDB client.

        :return: boto3 RDS client
        :rtype: boto3.client
        """
        if not self.aws_session:
            raise SmarterAWSException("AWS session is not initialized.")
        if not self._client:
            self._client = self.aws_session.client("rds")
        return self._client

    def get_mysql_info(self):
        """
        Return the version of the MySQL server

        :return: MySQL server information
        :rtype: dict
        """
        response = self.client.describe_db_instances(DBInstanceIdentifier=smarter_settings.aws_db_instance_identifier)
        response = response["DBInstances"][0]
        retval = {
            "Engine": response.get("Engine"),
            "EngineVersion": response.get("EngineVersion"),
        }
        return retval
