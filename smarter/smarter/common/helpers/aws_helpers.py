"""
AWS Helper Module.

Implements a singleton pattern for an aws helper class that provides abstractions
for commonly needed coding patterns in the AWS boto3 SDK. The helper class itself
receives its top-level configuration data from smarter.common.conf, a Pydantic
module that is populated from environment variables.

Individual AWS Services are implemented as classes in the aws module. The
AWSInfrastructureConfig class provides a single point of access to all AWS services.
The SingletonConfig class ensures that only one instance of the AWSInfrastructureConfig
class is created.

Individual services are accessed lazily via properties on the AWSInfrastructureConfig class.
"""

import logging
from typing import Optional

from smarter.common.mixins import Singleton

from .aws.acm import AWSCertificateManager
from .aws.api_gateway import AWSAPIGateway
from .aws.aws import AWSBase
from .aws.dynamodb import AWSDynamoDB
from .aws.eks import AWSEks
from .aws.exceptions import AWSNotReadyError
from .aws.iam import AWSIdentifyAccessManagement
from .aws.lambda_function import AWSLambdaFunction
from .aws.rds import AWSRds
from .aws.rekognition import AWSRekognition
from .aws.route53 import AWSRoute53
from .aws.s3 import AWSSimpleStorageSystem

logger = logging.getLogger(__name__)


class AWSInfrastructureConfig(metaclass=Singleton):
    """
    Provides a unified, singleton-based interface for accessing AWS services within the application.

    This class is designed to centralize and simplify interactions with various AWS services by exposing
    each service as a lazily-loaded property. When a property corresponding to a specific AWS service
    (such as S3, DynamoDB, Lambda, etc.) is accessed for the first time, the class will instantiate the
    appropriate service client and cache it for future use. This approach ensures that resources are only
    allocated when needed, improving efficiency and reducing unnecessary overhead.

    The configuration for AWS access (such as credentials and region) is sourced from environment variables
    and managed by the `smarter.common.conf` module, which uses Pydantic for validation and parsing.
    This allows the application to be easily configured for different environments without code changes.

    The singleton pattern is enforced via the `Singleton` metaclass, guaranteeing that only one instance
    of this configuration class exists throughout the application's lifecycle. This ensures consistent
    state and avoids redundant initialization of AWS service clients.

    The class provides convenient properties for each supported AWS service, including but not limited to:
    S3, DynamoDB, Lambda, IAM, RDS, Route53, Rekognition, ACM, API Gateway, and EKS. Each property checks
    if AWS is ready (properly configured and accessible) before instantiating the service client.

    In addition to service clients, the class exposes properties for retrieving AWS account metadata,
    such as the current identity, IAM ARN, and account ID, as well as the version of the underlying
    botocore library.

    This design enables developers to interact with AWS services in a consistent and Pythonic way,
    abstracting away the boilerplate of client initialization and configuration management. It also
    facilitates testing and maintenance by providing a single, well-defined entry point for all AWS
    interactions within the application.
    """

    _aws: Optional[AWSBase] = None
    _acm: Optional[AWSCertificateManager] = None
    _api_gateway: Optional[AWSAPIGateway] = None
    _dynamodb: Optional[AWSDynamoDB] = None
    _eks: Optional[AWSEks] = None
    _iam: Optional[AWSIdentifyAccessManagement] = None
    _lambda_function: Optional[AWSLambdaFunction] = None
    _rekognition: Optional[AWSRekognition] = None
    _route53: Optional[AWSRoute53] = None
    _s3: Optional[AWSSimpleStorageSystem] = None
    _rds: Optional[AWSRds] = None

    def ready(self) -> bool:
        """Check if AWS is ready"""
        return self.aws.ready

    @property
    def identity(self) -> Optional[dict]:
        """
        Return the AWS identity.

        :return: AWS identity dictionary or None if not available.
        :rtype: Optional[dict]
        """
        return self.aws.identity

    @property
    def aws_iam_arn(self) -> Optional[str]:
        """
        Return the AWS IAM ARN.

        :return: AWS IAM ARN or None if not available.
        :rtype: Optional[str]
        """
        return self.aws.aws_iam_arn

    @property
    def aws_account_id(self) -> Optional[str]:
        """
        Return the AWS Account ID.

        :return: AWS Account ID or None if not available.
        :rtype: Optional[str]
        """
        return self.aws.aws_account_id

    @property
    def get_botocore_version(self) -> str:
        """
        Return the botocore version

        :return: Botocore version string.
        :rtype: str
        """
        return self.aws.version

    @property
    def aws(self) -> AWSBase:
        """
        Return the AWS Base

        :return: AWSBase instance.
        :rtype: AWSBase
        """
        if not self._aws:
            self._aws = AWSBase()
        return self._aws

    @property
    def acm(self) -> AWSCertificateManager:
        """
        Return the AWS Certificate Manager

        :return: AWSCertificateManager instance.
        :rtype: AWSCertificateManager
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._acm:
            self._acm = AWSCertificateManager()
        return self._acm

    @property
    def api_gateway(self) -> AWSAPIGateway:
        """
        Return the AWS API Gateway

        :return: AWSAPIGateway instance.
        :rtype: AWSAPIGateway
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._api_gateway:
            self._api_gateway = AWSAPIGateway()
        return self._api_gateway

    @property
    def dynamodb(self) -> AWSDynamoDB:
        """
        Return the AWS DynamoDB

        :return: AWSDynamoDB instance.
        :rtype: AWSDynamoDB
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._dynamodb:
            self._dynamodb = AWSDynamoDB()
        return self._dynamodb

    @property
    def eks(self) -> AWSEks:
        """
        Return the AWS EKS

        :return: AWSEks instance.
        :rtype: AWSEks
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._eks:
            self._eks = AWSEks()
        return self._eks

    @property
    def lambda_function(self) -> AWSLambdaFunction:
        """
        Return the AWS Lambda Function

        :return: AWSLambdaFunction instance.
        :rtype: AWSLambdaFunction
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._lambda_function:
            self._lambda_function = AWSLambdaFunction()
        return self._lambda_function

    @property
    def iam(self) -> AWSIdentifyAccessManagement:
        """
        Return the AWS IAM

        :return: AWSIdentifyAccessManagement instance.
        :rtype: AWSIdentifyAccessManagement
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._iam:
            self._iam = AWSIdentifyAccessManagement()
        return self._iam

    @property
    def rds(self) -> AWSRds:
        """
        Return the AWS RDS

        :return: AWSRds instance.
        :rtype: AWSRds
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._rds:
            self._rds = AWSRds()
        return self._rds

    @property
    def rekognition(self) -> AWSRekognition:
        """
        Return the AWS Rekognition

        :return: AWSRekognition instance.
        :rtype: AWSRekognition
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._rekognition:
            self._rekognition = AWSRekognition()
        return self._rekognition

    @property
    def route53(self) -> AWSRoute53:
        """
        Return the AWS Route53

        :return: AWSRoute53 instance.
        :rtype: AWSRoute53
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._route53:
            self._route53 = AWSRoute53()
        return self._route53

    @property
    def s3(self) -> AWSSimpleStorageSystem:
        """
        Return the AWS S3

        :return: AWSSimpleStorageSystem instance.
        :rtype: AWSSimpleStorageSystem
        """
        if not self.ready():
            raise AWSNotReadyError("AWS is not ready. Please check your AWS configuration.")
        if not self._s3:
            self._s3 = AWSSimpleStorageSystem()
        return self._s3


aws_helper = AWSInfrastructureConfig()
