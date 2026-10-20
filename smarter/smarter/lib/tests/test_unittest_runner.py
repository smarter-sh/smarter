"""Test :mod:`smarter.lib.unittest.runner`, and its JUnit XML report."""

import io
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET  # nosec B405: parses a report that this test writes
from unittest import mock

from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.runner import (
    INFRASTRUCTURE,
    JUNIT_XML_ENVIRONMENT_VARIABLE,
    SmarterTestRunner,
    junit_xml_path,
)


def environ_without_report() -> dict[str, str]:
    """The current environment, without SMARTER_TEST_JUNIT_XML, which CI sets for the outer test run."""
    return {name: value for name, value in os.environ.items() if name != JUNIT_XML_ENVIRONMENT_VARIABLE}


def example_suite() -> unittest.TestSuite:
    """
    A suite with one passing, one failing and one skipped test.

    The TestCase is defined inside a function, so that test discovery doesn't run it.
    """

    class Example(unittest.TestCase):
        """Example tests for the runner to run."""

        def test_passes(self):
            self.assertTrue(True)

        def test_fails(self):
            self.assertEqual(1, 2)

        @unittest.skip("example")
        def test_skipped(self):
            pass

    return unittest.defaultTestLoader.loadTestsFromTestCase(Example)


class TestJunitXmlPath(SmarterTestBase):
    """Test how SMARTER_TEST_JUNIT_XML is read."""

    def test_unset(self):
        with mock.patch.dict(os.environ, environ_without_report(), clear=True):
            self.assertIsNone(junit_xml_path())

    def test_blank(self):
        with mock.patch.dict(os.environ, {JUNIT_XML_ENVIRONMENT_VARIABLE: "  "}):
            self.assertIsNone(junit_xml_path())

    def test_path(self):
        with mock.patch.dict(os.environ, {JUNIT_XML_ENVIRONMENT_VARIABLE: " reports/tests.xml "}):
            self.assertEqual(junit_xml_path(), "reports/tests.xml")


class TestSmarterTestRunner(SmarterTestBase):
    """Test the runner's infrastructure tag and its JUnit XML report."""

    def setUp(self):
        super().setUp()
        self.directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)
        super().tearDown()

    def run_example_suite(self, environ: dict[str, str]) -> unittest.TestResult:
        with mock.patch.dict(os.environ, environ, clear=True), mock.patch("sys.stderr", io.StringIO()):
            runner = SmarterTestRunner(verbosity=0)
            return runner.run_suite(example_suite())

    def test_skips_infrastructure_by_default(self):
        self.assertIn(INFRASTRUCTURE, SmarterTestRunner(verbosity=0).exclude_tags)

    def test_without_report(self):
        result = self.run_example_suite(environ_without_report())
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(len(result.skipped), 1)
        self.assertEqual(os.listdir(self.directory), [])

    def test_writes_report(self):
        path = os.path.join(self.directory, "reports", "tests.xml")
        result = self.run_example_suite({**environ_without_report(), JUNIT_XML_ENVIRONMENT_VARIABLE: path})

        self.assertEqual(result.testsRun, 3)
        self.assertEqual(len(result.failures), 1)
        self.assertTrue(os.path.isfile(path))

        root = ET.parse(path).getroot()  # nosec B314: this test wrote the file
        cases = {case.get("name"): case for case in root.iter("testcase")}
        self.assertEqual(set(cases), {"test_passes", "test_fails", "test_skipped"})
        self.assertIsNotNone(cases["test_fails"].find("failure"))
        self.assertIsNotNone(cases["test_skipped"].find("skipped"))
        self.assertIsNone(cases["test_passes"].find("failure"))

    def test_report_has_no_result_class(self):
        with mock.patch.dict(os.environ, {JUNIT_XML_ENVIRONMENT_VARIABLE: "tests.xml"}):
            runner = SmarterTestRunner(verbosity=0, debug_sql=True)
            self.assertIsNone(runner.get_test_runner_kwargs()["resultclass"])
        with mock.patch.dict(os.environ, environ_without_report(), clear=True):
            runner = SmarterTestRunner(verbosity=0, debug_sql=True)
            self.assertIsNotNone(runner.get_test_runner_kwargs()["resultclass"])

    def test_restores_test_runner(self):
        path = os.path.join(self.directory, "tests.xml")
        with (
            mock.patch.dict(os.environ, {JUNIT_XML_ENVIRONMENT_VARIABLE: path}),
            mock.patch("sys.stderr", io.StringIO()),
        ):
            runner = SmarterTestRunner(verbosity=0)
            runner.run_suite(example_suite())
        self.assertIs(runner.test_runner, unittest.TextTestRunner)
