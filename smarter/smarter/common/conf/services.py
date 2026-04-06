"""
Services enabled for this solution. This is intended to be permanently read-only
"""

import logging
from functools import lru_cache  # utility for caching function/method results
from typing import List, Tuple, Union  # type hint utilities

import boto3  # AWS SDK for Python https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
from botocore.exceptions import (
    EndpointConnectionError,
    NoCredentialsError,
    ProfileNotFound,
)

from smarter.common.conf.const import get_env
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}.Services")


class Services:
    """Services enabled for this solution. This is intended to be permanently read-only"""

    # enabled
    AWS_CLI = ("aws-cli", True)
    AWS_ROUTE53 = ("route53", True)
    AWS_S3 = ("s3", True)
    AWS_EC2 = ("ec2", True)
    AWS_IAM = ("iam", True)
    AWS_CLOUDWATCH = ("cloudwatch", True)
    AWS_SES = ("ses", True)
    AWS_RDS = ("rds", True)
    AWS_EKS = ("eks", True)

    # disabled
    AWS_LAMBDA = ("lambda", False)
    AWS_APIGATEWAY = ("apigateway", False)
    AWS_SNS = ("sns", False)
    AWS_SQS = ("sqs", False)
    AWS_REKOGNITION = ("rekognition", False)
    AWS_DYNAMODB = ("dynamodb", False)

    @classmethod
    def is_connected_to_aws(cls) -> bool:

        try:
            logger.debug(
                "%s.is_connected_to_aws(): Checking if AWS credentials are available and valid.", logger_prefix
            )
            retval = bool(boto3.Session().get_credentials())
            if not retval:
                logger.warning(
                    "%s.is_connected_to_aws(): AWS is not configured properly. Credentials are invalid, or no credentials were found.",
                    logger_prefix,
                )
                return False

            logger.debug("%s.is_connected_to_aws(): Attempting to connect to AWS using boto3", logger_prefix)
            session = boto3.Session()
            sts = session.client("sts")
            logger.debug(
                "%s.is_connected_to_aws(): Checking AWS connectivity by calling sts.get_caller_identity()",
                logger_prefix,
            )
            sts.get_caller_identity()
            return True
        except (NoCredentialsError, ProfileNotFound, EndpointConnectionError):
            logger.warning(
                "%s.is_connected_to_aws(): AWS is not configured properly. Credentials are invalid, or no credentials were found.",
                logger_prefix,
            )
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.warning("%s.is_connected_to_aws(): Failed to connect to AWS: %s", logger_prefix, e)
            return False

    @classmethod
    def enabled(cls, service: Union[str, Tuple[str, bool]]) -> bool:
        """Is the service enabled?"""
        if not cls.is_connected_to_aws():
            return False
        if isinstance(service, tuple):
            service = service[0]
        return service in cls.enabled_services()

    @classmethod
    def raise_error_on_disabled(cls, service: Union[str, Tuple[str, bool]]) -> None:
        """Raise an error if the service is disabled"""
        if not cls.enabled(service):
            if Services.is_connected_to_aws():
                raise SmarterConfigurationError(f"{service} is not enabled. See conf.Services")
            else:
                logger.warning("AWS is not configured. %s is not enabled.", service)

    @classmethod
    def to_dict(cls):
        """Convert Services to dict"""
        return {
            key: value
            for key, value in Services.__dict__.items()
            if not key.startswith("__")
            and not callable(key)
            and key not in ["enabled", "raise_error_on_disabled", "to_dict", "enabled_services"]
        }

    @classmethod
    def enabled_services(cls) -> List[str]:
        """Return a list of enabled services"""
        return [
            getattr(cls, key)[0]
            for key in dir(cls)
            if not key.startswith("__")
            and not callable(getattr(cls, key))
            and key not in ["enabled", "raise_error_on_disabled", "to_dict", "enabled_services"]
            and getattr(cls, key)[1] is True
        ]


AWS_REGIONS = ["us-east-1"]
AWS_REGION = get_env("AWS_REGION", default=AWS_REGIONS[0])
if Services.enabled(Services.AWS_EC2):
    try:
        ec2 = boto3.Session(region_name=AWS_REGION).client("ec2")
        regions = ec2.describe_regions()
        AWS_REGIONS = [region["RegionName"] for region in regions["Regions"]]
    except (ProfileNotFound, NoCredentialsError):
        logger.warning("could not initialize ec2 client")
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("unexpected error initializing aws ec2 client: %s", e)


@lru_cache(maxsize=1)
def get_services() -> Services:
    """Get the singleton instance."""
    try:
        return Services()
    except Exception as e:
        raise SmarterConfigurationError("Invalid configuration: " + str(e)) from e


services = get_services()

__all__ = ["services"]
