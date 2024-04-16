# pylint: disable=wrong-import-position
# pylint: disable=duplicate-code
"""Test configuration Settings class."""

# python stuff
import os
import sys
import unittest
from pathlib import Path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402

from smarter.common.helpers.aws_helpers import aws_helper


class TestAWSInfrastructure(unittest.TestCase):
    """Test AWS infrastructure."""

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------
    def test_aws_connection_works(self):
        """Test that the AWS connection works."""
        self.assertTrue(aws_helper.aws.ready(), "AWS connection failed.")
