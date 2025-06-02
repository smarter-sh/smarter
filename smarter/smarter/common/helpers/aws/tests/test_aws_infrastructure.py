# pylint: disable=wrong-import-position
# pylint: disable=duplicate-code
"""Test configuration Settings class."""

# python stuff
import os
import sys
from pathlib import Path

from smarter.lib.unittest.base_classes import SmarterTestBase


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402

from smarter.common.helpers.aws_helpers import aws_helper


class TestAWSInfrastructure(SmarterTestBase):
    """Test AWS infrastructure."""

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------
    def test_aws_connection_works(self):
        """Test that the AWS connection works."""
        self.assertTrue(aws_helper.aws.ready, "AWS connection failed.")
