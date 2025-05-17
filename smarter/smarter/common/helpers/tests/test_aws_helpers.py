"""Test AWSInfrastructureConfig class."""

from unittest.mock import patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..aws_helpers import AWSInfrastructureConfig


class TestAWSInfrastructureConfig(SmarterTestBase):
    """Test AWSInfrastructureConfig class."""

    def setUp(self):
        # Clear singleton instance for each test
        AWSInfrastructureConfig._instances = {}

    @patch("smarter.common.helpers.aws_helpers.AWSBase")
    def test_aws_property_lazy(self, mock_awsbase):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._aws)
        aws_instance = mock_awsbase.return_value
        result = config.aws
        self.assertEqual(result, aws_instance)
        self.assertIs(config._aws, aws_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSCertificateManager")
    def test_acm_property_lazy(self, mock_acm):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._acm)
        acm_instance = mock_acm.return_value
        result = config.acm
        self.assertEqual(result, acm_instance)
        self.assertIs(config._acm, acm_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSAPIGateway")
    def test_api_gateway_property_lazy(self, mock_api):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._api_gateway)
        api_instance = mock_api.return_value
        result = config.api_gateway
        self.assertEqual(result, api_instance)
        self.assertIs(config._api_gateway, api_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSDynamoDB")
    def test_dynamodb_property_lazy(self, mock_ddb):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._dynamodb)
        ddb_instance = mock_ddb.return_value
        result = config.dynamodb
        self.assertEqual(result, ddb_instance)
        self.assertIs(config._dynamodb, ddb_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSEks")
    def test_eks_property_lazy(self, mock_eks):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._eks)
        eks_instance = mock_eks.return_value
        result = config.eks
        self.assertEqual(result, eks_instance)
        self.assertIs(config._eks, eks_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSLambdaFunction")
    def test_lambda_function_property_lazy(self, mock_lambda):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._lambda_function)
        lambda_instance = mock_lambda.return_value
        result = config.lambda_function
        self.assertEqual(result, lambda_instance)
        self.assertIs(config._lambda_function, lambda_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSIdentifyAccessManagement")
    def test_iam_property_lazy(self, mock_iam):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._iam)
        iam_instance = mock_iam.return_value
        result = config.iam
        self.assertEqual(result, iam_instance)
        self.assertIs(config._iam, iam_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSRds")
    def test_rds_property_lazy(self, mock_rds):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._rds)
        rds_instance = mock_rds.return_value
        result = config.rds
        self.assertEqual(result, rds_instance)
        self.assertIs(config._rds, rds_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSRekognition")
    def test_rekognition_property_lazy(self, mock_rekognition):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._rekognition)
        rekognition_instance = mock_rekognition.return_value
        result = config.rekognition
        self.assertEqual(result, rekognition_instance)
        self.assertIs(config._rekognition, rekognition_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSRoute53")
    def test_route53_property_lazy(self, mock_route53):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._route53)
        route53_instance = mock_route53.return_value
        result = config.route53
        self.assertEqual(result, route53_instance)
        self.assertIs(config._route53, route53_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSSimpleStorageSystem")
    def test_s3_property_lazy(self, mock_s3):
        config = AWSInfrastructureConfig()
        self.assertIsNone(config._s3)
        s3_instance = mock_s3.return_value
        result = config.s3
        self.assertEqual(result, s3_instance)
        self.assertIs(config._s3, s3_instance)

    @patch("smarter.common.helpers.aws_helpers.AWSBase")
    def test_get_botocore_version(self, mock_awsbase):
        config = AWSInfrastructureConfig()
        aws_instance = mock_awsbase.return_value
        aws_instance.get_botocore_version.return_value = "1.34.0"
        version = config.get_botocore_version
        self.assertEqual(version, "1.34.0")
