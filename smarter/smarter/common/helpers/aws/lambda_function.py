"""AWS Lambda helper class."""

import logging

from .aws import AWSBase
from .exceptions import AWSNotReadyError

logger = logging.getLogger(__name__)


class AWSLambdaFunction(AWSBase):
    """AWS Lambda helper class."""

    _client = None
    _client_type: str = "lambda"

    def get_lambdas(self) -> dict[str, str]:
        """Return a dict of the AWS Lambdas."""
        if not self.ready or not self.client:
            raise AWSNotReadyError(f"{self.formatted_class_name} is not ready to interact with AWS Lambda.")
        lambdas = self.client.list_functions()["Functions"]
        retval = {
            lambda_function["FunctionName"]: lambda_function["FunctionArn"]
            for lambda_function in lambdas
            if self.shared_resource_identifier in lambda_function["FunctionName"]
        }
        return retval or {}
