"""AWS helper base class."""

# python stuff
import logging
import os
import socket

# our stuff
from smarter.common.conf import Services
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.utils import recursive_sort_dict


logger = logging.getLogger(__name__)


class AWSBase:
    """AWS helper base class."""

    _domain = None
    _aws_session = None
    _environment_domain: str = None
    _shared_resource_identifier = None

    def __init__(self, shared_resource_identifier: str = smarter_settings.shared_resource_identifier):
        self._shared_resource_identifier = shared_resource_identifier
        if not self.is_aws_environment:
            logger.warning("AWS invoked for non-AWS environment: %s.", smarter_settings.environment)

    @property
    def is_aws_environment(self) -> bool:
        """Return True if the environment is AWS."""
        return smarter_settings.environment in SmarterEnvironments.aws_environments

    @property
    def aws_session(self):
        """Return the AWS session."""
        if not self._aws_session:
            self._aws_session = smarter_settings.aws_session
        return self._aws_session

    @property
    def shared_resource_identifier(self):
        """Return the shared resource identifier."""
        return self._shared_resource_identifier

    @property
    def environment_domain(self) -> str:
        """Return the environment domain."""
        if not self._environment_domain:
            self._environment_domain = smarter_settings.environment_domain
        return self._environment_domain

    @property
    def dump(self):
        """Return a dict of the AWS infrastructure config."""
        retval = {}
        if Services.enabled(Services.AWS_APIGATEWAY):
            api = self.get_api(smarter_settings.aws_apigateway_name)
            retval["apigateway"] = {
                "api_id": api.get("id"),
                "stage": self.get_api_stage(),
                "domains": self.get_api_custom_domains(),
            }
        if Services.enabled(Services.AWS_S3):
            retval["s3"] = {"bucket_name": self.get_bucket_by_prefix(smarter_settings.aws_s3_bucket_name)}
        if Services.enabled(Services.AWS_DYNAMODB):
            retval["dynamodb"] = {"table_name": self.get_dyanmodb_table_by_name(smarter_settings.aws_dynamodb_table_id)}
        if Services.enabled(Services.AWS_REKOGNITION):
            retval["rekognition"] = {
                "collection_id": self.get_rekognition_collection_by_id(smarter_settings.aws_rekognition_collection_id)
            }
        if Services.enabled(Services.AWS_IAM):
            retval["iam"] = {"policies": self.get_iam_policies(), "roles": self.get_iam_roles()}
        if Services.enabled(Services.AWS_LAMBDA):
            retval["lambda"] = self.get_lambdas()
        if Services.enabled(Services.AWS_ROUTE53) and Services.enabled(Services.AWS_APIGATEWAY):
            retval["route53"] = self.get_dns_record_from_hosted_zone()
        return recursive_sort_dict(retval)

    def get_url(self, path) -> str:
        """Return the url for the given path."""
        if smarter_settings.aws_apigateway_create_custom_domaim:
            return f"https://{smarter_settings.aws_apigateway_domain_name}{path}"
        return f"https://{smarter_settings.aws_apigateway_domain_name}/{self.get_api_stage()}{path}"

    def aws_connection_works(self):
        """Test that the AWS connection works."""
        try:
            # pylint: disable=pointless-statement
            smarter_settings.aws_session.region_name
            return True
        except Exception:  # pylint: disable=broad-exception-caught
            return False

    @property
    def domain(self):
        """Return the domain."""
        if not self._domain:
            if smarter_settings.aws_apigateway_create_custom_domaim:
                self._domain = (
                    os.getenv(key="DOMAIN")
                    or "api." + smarter_settings.shared_resource_identifier + "." + smarter_settings.root_domain
                )
                return self._domain

            response = smarter_settings.aws_apigateway_client.get_rest_apis()
            for item in response["items"]:
                if item["name"] == self.api_gateway_name:
                    api_id = item["id"]
                    self._domain = f"{api_id}.execute-api.{smarter_settings.aws_region}.amazonaws.com"
        return self._domain

    def domain_exists(self) -> bool:
        """Test that the domain exists."""
        try:
            socket.gethostbyname(smarter_settings.aws_apigateway_domain_name)
            return True
        except socket.gaierror:
            return False
