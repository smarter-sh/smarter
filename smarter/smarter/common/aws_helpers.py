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

from .aws.acm import AWSCertificateManager
from .aws.api_gateway import AWSAPIGateway
from .aws.aws import AWSBase
from .aws.dynamodb import AWSDynamoDB
from .aws.iam import AWSIdentifyAccessManagement
from .aws.lambda_function import AWSLambdaFunction
from .aws.rekognition import AWSRekognition
from .aws.route53 import AWSRoute53
from .aws.s3 import AWSSimpleStorageSystem
from .classes import Singleton


# pylint: disable=too-many-instance-attributes
class AWSInfrastructureConfig(metaclass=Singleton):
    """AWS Infrastructure Configuration class with lazy loading of services."""

    _aws: AWSBase = None
    _acm: AWSCertificateManager = None
    _api_gateway: AWSAPIGateway = None
    _dynamodb: AWSDynamoDB = None
    _iam: AWSIdentifyAccessManagement = None
    _lambda_function: AWSLambdaFunction = None
    _rekognition: AWSRekognition = None
    _route53: AWSRoute53 = None
    _s3: AWSSimpleStorageSystem = None

    @property
    def aws(self) -> AWSBase:
        """Return the AWS Base"""
        if not self._aws:
            self._aws = AWSBase()
        return self._aws

    @property
    def acm(self) -> AWSCertificateManager:
        """Return the AWS Certificate Manager"""
        if not self._acm:
            self._acm = AWSCertificateManager()
        return self._acm

    @property
    def api_gateway(self) -> AWSAPIGateway:
        """Return the AWS API Gateway"""
        if not self._api_gateway:
            self._api_gateway = AWSAPIGateway()
        return self._api_gateway

    @property
    def dynamodb(self) -> AWSDynamoDB:
        """Return the AWS DynamoDB"""
        if not self._dynamodb:
            self._dynamodb = AWSDynamoDB()
        return self._dynamodb

    @property
    def lambda_function(self) -> AWSLambdaFunction:
        """Return the AWS Lambda Function"""
        if not self._lambda_function:
            self._lambda_function = AWSLambdaFunction()
        return self._lambda_function

    @property
    def iam(self) -> AWSIdentifyAccessManagement:
        """Return the AWS IAM"""
        if not self._iam:
            self._iam = AWSIdentifyAccessManagement()
        return self._iam

    @property
    def rekognition(self) -> AWSRekognition:
        """Return the AWS Rekognition"""
        if not self._rekognition:
            self._rekognition = AWSRekognition()
        return self._rekognition

    @property
    def route53(self) -> AWSRoute53:
        """Return the AWS Route53"""
        if not self._route53:
            self._route53 = AWSRoute53()
        return self._route53

    @property
    def s3(self) -> AWSSimpleStorageSystem:
        """Return the AWS S3"""
        if not self._s3:
            self._s3 = AWSSimpleStorageSystem()
        return self._s3


aws_helper = AWSInfrastructureConfig()
