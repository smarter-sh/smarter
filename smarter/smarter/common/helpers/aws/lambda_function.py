"""AWS Lambda helper class."""

import logging

from .aws import AWSBase


logger = logging.getLogger(__name__)


class AWSLambdaFunction(AWSBase):
    """AWS Lambda helper class."""

    _client = None
    _client_type: str = "lambda"

    def get_lambdas(self):
        """Return a dict of the AWS Lambdas."""
        lambdas = self.client.list_functions()["Functions"]
        retval = {
            lambda_function["FunctionName"]: lambda_function["FunctionArn"]
            for lambda_function in lambdas
            if self.shared_resource_identifier in lambda_function["FunctionName"]
        }
        return retval or {}
