# pylint: disable=wrong-import-position
"""Test Vectorstore tasks."""

# python stuff
from smarter.lib import logging

from .test_base import VectorstoreTestBase

logger = logging.getLogger(__name__)


class TestVectorstoreTasks(VectorstoreTestBase):
    """Test Vectorstore tasks."""

    def test_load_pdf(self):
        pass
