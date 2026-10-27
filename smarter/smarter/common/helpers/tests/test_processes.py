"""Test the helpers for code that runs once per server."""

import os
import tempfile
from unittest.mock import patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..processes import is_first_worker

MODULE = "smarter.common.helpers.processes"


class TestIsFirstWorker(SmarterTestBase):
    """Test is_first_worker()."""

    def _marker(self, name: str, ppid: int) -> str:
        marker = os.path.join(tempfile.gettempdir(), f"smarter-{name}-{ppid}")
        self.addCleanup(lambda: os.path.exists(marker) and os.remove(marker))
        return marker

    def test_only_the_first_worker_is_first(self):
        ppid = 2_000_000_000 + os.getpid()
        self._marker("test-first", ppid)
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            patch(f"{MODULE}.os.getppid", return_value=ppid),
        ):
            self.assertTrue(is_first_worker("test-first"))
            self.assertFalse(is_first_worker("test-first"))

    def test_each_name_has_its_own_marker(self):
        ppid = 2_000_000_000 + os.getpid()
        self._marker("test-a", ppid)
        self._marker("test-b", ppid)
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            patch(f"{MODULE}.os.getppid", return_value=ppid),
        ):
            self.assertTrue(is_first_worker("test-a"))
            self.assertTrue(is_first_worker("test-b"))
            self.assertFalse(is_first_worker("test-a"))

    def test_a_single_process_is_always_first(self):
        with patch(f"{MODULE}.multiprocessing.parent_process", return_value=None):
            self.assertTrue(is_first_worker("test-single"))
            self.assertTrue(is_first_worker("test-single"))

    def test_an_unwritable_temp_dir_is_first(self):
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            patch(f"{MODULE}.tempfile.gettempdir", return_value="/nonexistent"),
            patch(f"{MODULE}.os.open", side_effect=PermissionError),
        ):
            self.assertTrue(is_first_worker("test-unwritable"))
