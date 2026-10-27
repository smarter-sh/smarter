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
    SHARD_ENVIRONMENT_VARIABLE,
    SmarterTestRunner,
    junit_xml_path,
    requested_shard,
    shard_tests,
    testcase_class_name,
)

# A small module of real tests, for build_suite() to discover.
DISCOVERY_LABEL = "smarter.lib.tests.test_json"


def environ_without_report() -> dict[str, str]:
    """
    The current environment, without the variables that CI sets for the outer test run.

    These are SMARTER_TEST_JUNIT_XML and SMARTER_TEST_SHARD.
    """
    outer = (JUNIT_XML_ENVIRONMENT_VARIABLE, SHARD_ENVIRONMENT_VARIABLE)
    return {name: value for name, value in os.environ.items() if name not in outer}


def example_testcases() -> list[unittest.TestCase]:
    """
    Tests of four TestCases, with 5, 3, 2 and 1 tests, in an interleaved order.

    The TestCases are made inside a function, so that test discovery doesn't run them.
    """

    def make(name: str, size: int) -> type[unittest.TestCase]:
        methods = {f"test_{n}": lambda self: None for n in range(size)}
        return type(name, (unittest.TestCase,), methods)

    loader = unittest.defaultTestLoader
    cases = [make("Five", 5), make("Three", 3), make("Two", 2), make("One", 1)]
    tests = [list(loader.loadTestsFromTestCase(case)) for case in cases]
    interleaved = []
    while any(tests):
        for group in tests:
            if group:
                interleaved.append(group.pop(0))
    return interleaved


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


class TestRequestedShard(SmarterTestBase):
    """Test how SMARTER_TEST_SHARD is read."""

    def shard(self, value: str | None) -> tuple[int, int] | None:
        environ = environ_without_report()
        if value is not None:
            environ[SHARD_ENVIRONMENT_VARIABLE] = value
        with mock.patch.dict(os.environ, environ, clear=True):
            return requested_shard()

    def test_unset(self):
        self.assertIsNone(self.shard(None))

    def test_blank(self):
        self.assertIsNone(self.shard("  "))

    def test_shard(self):
        self.assertEqual(self.shard(" 2/8 "), (2, 8))
        self.assertEqual(self.shard("1/1"), (1, 1))

    def test_not_a_fraction(self):
        for value in ("2", "two/8", "2/8/1", "2-8"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.shard(value)

    def test_out_of_range(self):
        for value in ("0/8", "9/8", "1/0", "-1/8"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.shard(value)


class TestShardTests(SmarterTestBase):
    """Test how the suite is dealt out to shards."""

    def test_testcase_class_name(self):
        test = example_testcases()[0]
        self.assertEqual(testcase_class_name(test), f"{type(test).__module__}.Five")

    def test_every_test_runs_once(self):
        tests = example_testcases()
        for shards in (1, 2, 3, 4, 8):
            with self.subTest(shards=shards):
                parts = [shard_tests(tests, shard, shards) for shard in range(1, shards + 1)]
                combined = [test for part in parts for test in part]
                self.assertEqual(len(combined), len(tests))
                self.assertEqual({id(test) for test in combined}, {id(test) for test in tests})

    def test_keeps_testcases_whole(self):
        tests = example_testcases()
        for shard in (1, 2, 3):
            names = {testcase_class_name(test) for test in shard_tests(tests, shard, 3)}
            for test in tests:
                if testcase_class_name(test) in names:
                    self.assertIn(test, shard_tests(tests, shard, 3))

    def test_largest_first(self):
        """5 goes to shard 1, then 3 and 2 to shard 2, then 1 to the first of the two equal shards."""
        tests = example_testcases()
        sizes = [len(shard_tests(tests, shard, 2)) for shard in (1, 2)]
        self.assertEqual(sizes, [6, 5])

    def test_keeps_order(self):
        tests = example_testcases()
        part = shard_tests(tests, 2, 2)
        self.assertEqual(part, [test for test in tests if test in part])

    def test_more_shards_than_testcases(self):
        tests = example_testcases()
        self.assertEqual(shard_tests(tests, 8, 8), [])


class TestBuildSuiteShard(SmarterTestBase):
    """Test that the runner builds only the requested shard of the suite."""

    def build(self, shard: str | None, **kwargs) -> unittest.TestSuite:
        environ = environ_without_report()
        if shard is not None:
            environ[SHARD_ENVIRONMENT_VARIABLE] = shard
        with mock.patch.dict(os.environ, environ, clear=True):
            return SmarterTestRunner(verbosity=0, **kwargs).build_suite([DISCOVERY_LABEL])

    @staticmethod
    def ids(suite: unittest.TestSuite) -> list[str]:
        return [test.id() for test in suite]

    def test_without_shard(self):
        self.assertGreater(len(self.ids(self.build(None))), 0)

    def test_shards_cover_the_suite(self):
        everything = self.ids(self.build(None))
        parts = [self.ids(self.build(f"{shard}/2")) for shard in (1, 2)]
        self.assertEqual(sorted(parts[0] + parts[1]), sorted(everything))
        self.assertFalse(set(parts[0]) & set(parts[1]))

    def test_logs_the_shard(self):
        environ = {**environ_without_report(), SHARD_ENVIRONMENT_VARIABLE: "1/2"}
        with mock.patch.dict(os.environ, environ, clear=True), mock.patch("sys.stdout", io.StringIO()) as stdout:
            SmarterTestRunner(verbosity=1).build_suite([DISCOVERY_LABEL])
        self.assertIn("Running shard 1 of 2:", stdout.getvalue())

    def test_rejects_parallel(self):
        with mock.patch.object(SmarterTestRunner, "parallel_test_suite", unittest.TestSuite):
            with self.assertRaises(ValueError):
                self.build("1/2")
