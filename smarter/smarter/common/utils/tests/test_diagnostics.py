"""Test diagnostics utility functions."""

from smarter.common.utils.diagnostics import get_diagnostics
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestDiagnosticsUtils(SmarterTestBase):
    """Test diagnostics utility functions."""

    def test_get_diagnostics_top_level_keys(self):
        diag = get_diagnostics()
        self.assertIsInstance(diag, dict)
        self.assertIn("created_at", diag)
        self.assertIn("environment", diag)

    def test_get_diagnostics_platform_info(self):
        diag = get_diagnostics()
        env = diag["environment"]
        self.assertIn("platform", env)
        platform_info = env["platform"]
        self.assertIn("os", platform_info)
        self.assertIn("system", platform_info)
        self.assertIn("release", platform_info)
        os_info = platform_info["os"]
        self.assertIn("name", os_info)
        self.assertIn("cwd", os_info)
        self.assertIn("process_id", os_info)
        self.assertIn("parent_process_id", os_info)
        self.assertIn("start_time", os_info)
        self.assertIn("uptime_seconds", os_info)

    def test_get_diagnostics_python_info(self):
        diag = get_diagnostics()
        py = diag["environment"]["python"]
        self.assertIn("python_version", py)
        self.assertIn("python_implementation", py)
        self.assertIn("python_compiler", py)
        self.assertIn("python_build", py)
        self.assertIn("python_installed_packages", py)
        self.assertIsInstance(py["python_installed_packages"], list)
        self.assertIn("loaded_modules", py)
        self.assertIsInstance(py["loaded_modules"], list)

    def test_get_diagnostics_resources_info(self):
        diag = get_diagnostics()
        res = diag["environment"]["resources"]
        self.assertIn("memory_info", res)
        self.assertIn("cpu_percent", res)
        self.assertIn("open_files", res)
        self.assertIn("num_threads", res)
        self.assertIn("thread_info", res)
        self.assertIn("disk_usage", res)
        self.assertIsInstance(res["memory_info"], dict)
        self.assertIsInstance(res["open_files"], list)
        self.assertIsInstance(res["thread_info"], list)
        self.assertIsInstance(res["disk_usage"], dict)

    def test_get_diagnostics_network_info(self):
        diag = get_diagnostics()
        net = diag["environment"]["network"]
        self.assertIn("connections", net)
        self.assertIsInstance(net["connections"], list)
