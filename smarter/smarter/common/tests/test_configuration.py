"""Test configuration Settings class.

TODO: Add tests for: 480, 487, 531, 595, 602, 609, 612-617, 623, 626-631, 654, 662-664, 671-673, 686, 702, 710-712, 725, 740-741
"""

import os
import re

from django.test import tag
from dotenv import load_dotenv
from pydantic_core import ValidationError as PydanticValidationError

from smarter.common.conf import Settings, settings_defaults
from smarter.common.conf.services import Services
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import get_semantic_version
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.runner import INFRASTRUCTURE


# pylint: disable=too-many-public-methods
class TestConfiguration(SmarterTestBase):
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

    def test_conf_defaults(self):
        """Test that settings == settings_defaults when no .env is in use."""
        os.environ.clear()
        mock_settings = Settings(init_info="test_conf_defaults()")

        self.assertEqual(mock_settings.aws_region, settings_defaults.AWS_REGION)

        self.assertEqual(mock_settings.debug_mode, settings_defaults.DEBUG_MODE)

    def test_env_legal_nulls(self):
        """Test that settings handles missing .env values."""
        os.environ.clear()
        env_path = self.env_path(".env.test_legal_nulls")
        loaded = load_dotenv(env_path)
        self.assertTrue(loaded)

        mock_settings = Settings(init_info="test_env_legal_nulls()")

        self.assertEqual(mock_settings.aws_region, settings_defaults.AWS_REGION)

    def test_env_illegal_nulls(self):
        """Test that settings handles certain missing .env values."""
        os.environ.clear()
        env_path = self.env_path(".env.test_illegal_nulls")
        loaded = load_dotenv(env_path)
        self.assertTrue(loaded)

        Settings(init_info="test_env_illegal_nulls()")

    def test_env_overrides(self):
        """Test that settings takes custom .env values."""
        os.environ.clear()
        env_path = self.env_path(".env.test_01")
        loaded = load_dotenv(env_path)
        self.assertTrue(loaded)

        # aws_regions is the real region list only when AWS is reachable; otherwise AWS_REGIONS.
        mock_settings = Settings(aws_regions=["us-west-1"], init_info="test_env_overrides()")

        self.assertEqual(mock_settings.aws_region, "us-west-1")
        self.assertEqual(mock_settings.debug_mode, True)

    def test_configure_with_class_constructor(self):
        """Test that we can set values with the class constructor."""

        mock_settings = Settings(
            aws_regions=["eu-west-1"],
            aws_region="eu-west-1",
            debug_mode=True,
            init_info="test_configure_with_class_constructor()",
        )

        self.assertEqual(mock_settings.aws_region, "eu-west-1")
        self.assertEqual(mock_settings.debug_mode, True)

    def test_configure_neg_int_with_class_constructor(self):
        """Test that we cannot set negative int values with the class constructor."""

        with self.assertRaises(PydanticValidationError):
            Settings(face_detect_max_faces_count=-1)

        with self.assertRaises(PydanticValidationError):
            Settings(face_detect_threshold=-1)

    def test_readonly_settings(self):
        """Test that we can't set readonly values with the class constructor."""

        mock_settings = Settings(aws_regions=["eu-west-1"], aws_region="eu-west-1")
        # by name: some are read-only properties, and the others aren't attributes of Settings at all
        readonly_values: tuple[tuple[str, object], ...] = (
            ("aws_region", "us-west-1"),
            ("table_id", "TEST_facialrecognition"),
            ("collection_id", "TEST_facialrecognition-collection"),
            ("face_detect_attributes", "TEST_DEFAULT"),
            ("face_detect_quality_filter", "TEST_AUTO"),
            ("debug_mode", True),
            ("face_detect_max_faces_count", 25),
            ("face_detect_threshold", 25),
        )
        for name, value in readonly_values:
            with self.assertRaises(PydanticValidationError):
                setattr(mock_settings, name, value)

    def test_initialize_with_values(self):
        """Test that we can set values with the class constructor."""
        mock_settings = Settings(
            debug_mode=False,
            dump_defaults=False,
            aws_profile="test-profile",
            aws_regions=["eu-west-1"],
            aws_region="eu-west-1",
            root_domain="test-domain.com",
            shared_resource_identifier="TEST_shared_resource_identifier",
            init_info="test_initialize_with_values()",
        )
        self.assertEqual(mock_settings.debug_mode, False)
        self.assertEqual(mock_settings.dump_defaults, False)
        self.assertEqual(mock_settings.aws_profile, "test-profile")
        self.assertEqual(mock_settings.aws_region, "eu-west-1")
        self.assertEqual(mock_settings.root_domain, "test-domain.com")
        self.assertEqual(mock_settings.shared_resource_identifier, "TEST_shared_resource_identifier")

    def test_semantic_version(self):
        """Test that the semantic version conforms to a valid pattern."""
        version = get_semantic_version()
        self.assertIsNotNone(version)
        # semver, or a PEP 440 development release such as the 9999.9999.9999.dev9999 placeholder
        # in the source tree, which the release pipeline replaces.
        pattern = r"^\d+\.\d+\.\d+((-[0-9A-Za-z-\.]+)?(\+[0-9A-Za-z-\.]+)?|\.dev\d+)$"
        match = re.match(pattern, version)
        self.assertIsNotNone(match, f"{version} is not a valid semantic version")

    @tag(INFRASTRUCTURE)
    def test_services(self):
        """Test that the services are valid."""
        services = Services()
        self.assertIsNotNone(services)
        self.assertTrue(services.enabled(services.AWS_CLI))
        with self.assertRaises(SmarterConfigurationError):
            services.raise_error_on_disabled(services.AWS_DYNAMODB)
        self.assertIsInstance(services.to_dict(), dict)
        self.assertIn(services.AWS_CLI[0], services.enabled_services())

    @tag(INFRASTRUCTURE)
    def test_settings_aws_account_info(self):
        """Test that the AWS region is a region code, e.g. us-east-1, ca-central-1 or us-gov-west-1."""
        mock_settings = Settings(init_info="test_settings_aws_account_id()")
        aws_region = mock_settings.aws_region
        self.assertIsNotNone(aws_region)
        assert aws_region is not None
        # it was assertTrue(aws_region.isalpha), which tested the method, not its result, and so passed
        # for any region; a region code, which has hyphens and a digit, is never alphabetic.
        self.assertRegex(aws_region, r"^[a-z]{2}(-[a-z]+)+-[0-9]+$")
