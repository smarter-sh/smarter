# pylint: disable=wrong-import-position
"""Test configuration Settings class.

TODO: Add tests for: 480, 487, 531, 595, 602, 609, 612-617, 623, 626-631, 654, 662-664, 671-673, 686, 702, 710-712, 725, 740-741
"""

import os

# python stuff
import sys

from smarter.lib.unittest.base_classes import SmarterTestBase


PYTHON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(PYTHON_ROOT)  # noqa: E402

# our stuff
from smarter.common.helpers.aws.aws import AWSBase
from smarter.common.helpers.aws.exceptions import AWSNotReadyError


# pylint: disable=too-many-public-methods
class TestAWSConfiguration(SmarterTestBase):
    """Test configuration."""

    # Get the directory of the current script
    here = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        super().setUp()
        # Save current environment variables
        self.saved_env = dict(os.environ)

    def tearDown(self):
        # Restore environment variables
        os.environ.clear()
        os.environ.update(self.saved_env)
        super().tearDown()

    def env_path(self, filename):
        """Return the path to the .env file."""
        return os.path.join(self.here, filename)

    def test_invalid_aws_credentials(self):
        """Test that boto3 raises a validation error for environment variable with non-existent aws region code."""

        print("test_invalid_aws_credentials")
        with self.assertRaises(AWSNotReadyError):
            AWSBase(aws_access_key_id="bad-key", aws_secret_access_key="bad-secret", aws_region="invalid-region")

    def test_configure_with_class_constructor(self):
        """test that we can set values with the class constructor"""

        mock_aws = AWSBase(aws_region="eu-west-1", debug_mode=True, init_info="test_configure_with_class_constructor()")

        self.assertEqual(mock_aws.aws_region, "eu-west-1")
        self.assertEqual(mock_aws.debug_mode, True)

    def test_settings_aws_account_id(self):
        """Test that the AWS account ID is valid."""
        mock_aws_base = AWSBase(init_info="test_settings_aws_account_id()")
        self.assertIsNotNone(mock_aws_base.aws_account_id)

    def test_settings_aws_session(self):
        """Test that the AWS session is valid."""
        mock_aws_base = AWSBase(init_info="test_settings_aws_session()")
        self.assertIsNotNone(mock_aws_base.aws_session)
        self.assertIsNotNone(mock_aws_base.aws_session.region_name)
        self.assertIsNotNone(mock_aws_base.aws_session.profile_name)
