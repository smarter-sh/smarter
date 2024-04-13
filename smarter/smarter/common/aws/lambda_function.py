"""AWS Lambda helper class."""

from .aws import AWSBase


class AWSLambdaFunction(AWSBase):
    """AWS Lambda helper class."""

    _client = None

    @property
    def client(self):
        """Return the AWS Lambda client."""
        if not self._client:
            self._client = self.aws_session.client("lambda")
        return self._client

    def get_lambdas(self):
        """Return a dict of the AWS Lambdas."""
        lambdas = self.client.list_functions()["Functions"]
        retval = {
            lambda_function["FunctionName"]: lambda_function["FunctionArn"]
            for lambda_function in lambdas
            if self.shared_resource_identifier in lambda_function["FunctionName"]
        }
        return retval or {}
