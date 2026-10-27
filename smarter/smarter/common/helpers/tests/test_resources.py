"""Test the helpers that compare a container's resource limits with what its server needs."""

import os
import tempfile
from unittest.mock import MagicMock, patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..resources import (
    cpu_limit,
    log_resource_limits,
    memory_limit_gib,
    recommended_cpu,
    recommended_memory_gib,
    uvicorn_workers,
    workers_from_command_line,
)

MODULE = "smarter.common.helpers.resources"


class ResourcesTestBase(SmarterTestBase):
    """Write fake cgroup and /proc files to a temporary directory."""

    def write(self, name: str, content: str) -> str:
        """Write content to a temporary file and return its path."""
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.addCleanup(os.rmdir, directory)
        self.addCleanup(os.remove, path)
        return path


class TestCpuLimit(ResourcesTestBase):
    """Test cpu_limit()."""

    def test_a_quota_is_rounded_up(self):
        with patch(f"{MODULE}.CGROUP_CPU_MAX", self.write("cpu.max", "150000 100000\n")):
            self.assertEqual(cpu_limit(), 2)

    def test_no_quota_falls_back_to_the_available_cores(self):
        with (
            patch(f"{MODULE}.CGROUP_CPU_MAX", self.write("cpu.max", "max 100000\n")),
            patch(f"{MODULE}.os.process_cpu_count", create=True, return_value=3),
        ):
            self.assertEqual(cpu_limit(), 3)

    def test_no_cgroup_falls_back_to_the_available_cores(self):
        with (
            patch(f"{MODULE}.CGROUP_CPU_MAX", "/nonexistent/cpu.max"),
            patch(f"{MODULE}.os.process_cpu_count", create=True, return_value=4),
        ):
            self.assertEqual(cpu_limit(), 4)

    def test_an_unknown_core_count_is_one(self):
        with (
            patch(f"{MODULE}.CGROUP_CPU_MAX", "/nonexistent/cpu.max"),
            patch(f"{MODULE}.os.process_cpu_count", create=True, return_value=None),
        ):
            self.assertEqual(cpu_limit(), 1)


class TestMemoryLimit(ResourcesTestBase):
    """Test memory_limit_gib()."""

    def test_a_limit_is_read_in_gib(self):
        with patch(f"{MODULE}.CGROUP_MEMORY_MAX", self.write("memory.max", f"{2 * 1024**3}\n")):
            self.assertEqual(memory_limit_gib(), 2.0)

    def test_no_limit_falls_back_to_meminfo(self):
        meminfo = self.write("meminfo", f"MemFree: 1 kB\nMemTotal: {8 * 1024**2} kB\n")
        with (
            patch(f"{MODULE}.CGROUP_MEMORY_MAX", self.write("memory.max", "max\n")),
            patch(f"{MODULE}.PROC_MEMINFO", meminfo),
        ):
            self.assertEqual(memory_limit_gib(), 8.0)

    def test_no_cgroup_falls_back_to_meminfo(self):
        with (
            patch(f"{MODULE}.CGROUP_MEMORY_MAX", "/nonexistent/memory.max"),
            patch(f"{MODULE}.PROC_MEMINFO", self.write("meminfo", f"MemTotal: {1024**2} kB\n")),
        ):
            self.assertEqual(memory_limit_gib(), 1.0)

    def test_meminfo_without_memtotal_is_an_error(self):
        with (
            patch(f"{MODULE}.CGROUP_MEMORY_MAX", "/nonexistent/memory.max"),
            patch(f"{MODULE}.PROC_MEMINFO", self.write("meminfo", "MemFree: 1 kB\n")),
        ):
            with self.assertRaises(ValueError):
                memory_limit_gib()


class TestUvicornWorkers(ResourcesTestBase):
    """Test workers_from_command_line() and uvicorn_workers()."""

    def test_workers_from_command_line(self):
        self.assertEqual(workers_from_command_line(["uvicorn", "app", "--workers=3"]), 3)
        self.assertEqual(workers_from_command_line(["uvicorn", "app", "--workers", "4"]), 4)
        self.assertIsNone(workers_from_command_line(["uvicorn", "app", "--workers"]))
        self.assertIsNone(workers_from_command_line(["uvicorn", "app"]))

    def test_a_single_process_is_one_worker(self):
        with patch(f"{MODULE}.multiprocessing.parent_process", return_value=None):
            self.assertEqual(uvicorn_workers(), 1)

    def _parent(self, cmdline: str):
        real_open = open
        path = self.write("cmdline", cmdline)
        return patch(
            f"{MODULE}.open",
            create=True,
            side_effect=lambda name, *a, **kw: real_open(path if name.endswith("/cmdline") else name, *a, **kw),
        )

    def test_a_spawned_worker_reads_its_parents_command_line(self):
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            self._parent("uvicorn\0smarter.asgi:application\0--workers=2\0"),
        ):
            self.assertEqual(uvicorn_workers(), 2)

    def test_web_concurrency_is_used_without_workers(self):
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            self._parent("uvicorn\0smarter.asgi:application\0"),
            patch.dict(os.environ, {"WEB_CONCURRENCY": "3"}),
        ):
            self.assertEqual(uvicorn_workers(), 3)

    def test_unreadable_parent_and_bad_web_concurrency_are_one_worker(self):
        with (
            patch(f"{MODULE}.multiprocessing.parent_process", return_value=object()),
            patch(f"{MODULE}.open", create=True, side_effect=OSError),
            patch.dict(os.environ, {"WEB_CONCURRENCY": "lots"}),
        ):
            self.assertEqual(uvicorn_workers(), 1)


class TestRecommendations(SmarterTestBase):
    """Test recommended_cpu() and recommended_memory_gib()."""

    def test_recommendations_grow_with_workers(self):
        self.assertEqual(recommended_cpu(0), 1)
        self.assertEqual(recommended_cpu(2), 2)
        self.assertEqual(recommended_memory_gib(1), 1.0)
        self.assertEqual(recommended_memory_gib(2), 1.5)
        self.assertEqual(recommended_memory_gib(4), 2.5)

    def test_the_helm_chart_defaults_are_enough(self):
        """2 workers in a pod limited to 2 cores and 2Gi, as in values.yaml, need no warning."""
        self.assertLessEqual(recommended_cpu(2), 2)
        self.assertLessEqual(recommended_memory_gib(2), 2.0)


class TestLogResourceLimits(SmarterTestBase):
    """Test log_resource_limits()."""

    def _log(self, cpu=2, memory=2.0, workers=2, first=True) -> MagicMock:
        logger = MagicMock()
        with (
            patch(f"{MODULE}.cpu_limit", return_value=cpu),
            patch(f"{MODULE}.memory_limit_gib", return_value=memory),
            patch(f"{MODULE}.uvicorn_workers", return_value=workers),
            patch(f"{MODULE}.is_first_worker", return_value=first),
        ):
            log_resource_limits(logger, "prefix")
        return logger

    def test_enough_resources_log_no_warning(self):
        logger = self._log()
        logger.warning.assert_not_called()
        self.assertTrue(logger.debug.call_args.args[0].startswith("%s.log_resource_limits()"))

    def test_too_little_is_warned_by_the_first_worker(self):
        logger = self._log(cpu=1, memory=1.0, workers=4)
        self.assertEqual(logger.warning.call_count, 2)
        cpu_warning, memory_warning = (c.args for c in logger.warning.call_args_list)
        self.assertEqual(cpu_warning[1:], ("prefix", 4, 4, 1))
        self.assertEqual(memory_warning[1:], ("prefix", 4, 2.5, 1.0))

    def test_the_other_workers_dont_warn(self):
        self._log(cpu=1, memory=1.0, workers=4, first=False).warning.assert_not_called()

    def test_unreadable_limits_are_a_warning(self):
        logger = MagicMock()
        with patch(f"{MODULE}.cpu_limit", side_effect=OSError("no cgroup")):
            log_resource_limits(logger, "prefix")
        self.assertIn("not available", logger.warning.call_args.args[0])

    def test_unparseable_limits_are_an_error(self):
        logger = MagicMock()
        with patch(f"{MODULE}.cpu_limit", side_effect=ValueError("bad")):
            log_resource_limits(logger, "prefix")
        self.assertIn("error parsing", logger.error.call_args.args[0])
