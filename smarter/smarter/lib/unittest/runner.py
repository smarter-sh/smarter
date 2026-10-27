"""
The Smarter test runner.

Some tests use real infrastructure: they deploy LLMClients to the Kubernetes cluster, and
create DNS records and certificates in AWS. They are slow, e.g. a deploy waits for a TLS
certificate for up to 40 minutes, which a local cluster never issues, and they need live
credentials. They are tagged :data:`INFRASTRUCTURE`, and skipped unless they are asked for:

.. code-block:: console

    python manage.py test                                    # everything else
    python manage.py test --tag infrastructure               # only the infrastructure tests
    SMARTER_TEST_INFRASTRUCTURE=true python manage.py test   # everything

Tag a test, or a whole TestCase, that uses real infrastructure:

.. code-block:: python

    from django.test import tag
    from smarter.lib.unittest.runner import INFRASTRUCTURE

    @tag(INFRASTRUCTURE)
    class TestDeploy(TestAccountMixin):
        ...

To also write the results as a JUnit XML report, for example for the job summary of a
GitHub Actions run, name the report file in :data:`JUNIT_XML_ENVIRONMENT_VARIABLE`:

.. code-block:: console

    SMARTER_TEST_JUNIT_XML=test-results.xml python manage.py test

The report is written by `unittest-xml-reporting <https://pypi.org/project/unittest-xml-reporting/>`_,
which is installed from ``requirements/local.txt``.

To run only one part of the suite, name it in :data:`SHARD_ENVIRONMENT_VARIABLE` as
``<shard>/<shards>``. GitHub Actions runs the suite as eight shards, side by side, on eight
runners:

.. code-block:: console

    SMARTER_TEST_SHARD=2/8 python manage.py test smarter

Every shard discovers the same tests and deals them out the same way (see :func:`shard_tests`),
so the shards together run each test exactly once.
"""

import collections
import functools
import os
import unittest

from django.test.runner import DiscoverRunner, iter_test_cases

INFRASTRUCTURE = "infrastructure"
"""The tag of tests that use real infrastructure: Kubernetes, AWS Route53, ACM, and so on."""
ENVIRONMENT_VARIABLE = "SMARTER_TEST_INFRASTRUCTURE"
JUNIT_XML_ENVIRONMENT_VARIABLE = "SMARTER_TEST_JUNIT_XML"
"""The environment variable that names the file to write a JUnit XML report of the test results to."""
SHARD_ENVIRONMENT_VARIABLE = "SMARTER_TEST_SHARD"
"""The environment variable that picks the part of the suite to run, as ``<shard>/<shards>``, e.g. ``2/8``."""


def include_infrastructure() -> bool:
    """Whether SMARTER_TEST_INFRASTRUCTURE asks for the infrastructure tests to run too."""
    return os.environ.get(ENVIRONMENT_VARIABLE, "").strip().lower() in ("1", "true", "yes")


def junit_xml_path() -> str | None:
    """The file that SMARTER_TEST_JUNIT_XML asks for a JUnit XML report to be written to, if any."""
    return os.environ.get(JUNIT_XML_ENVIRONMENT_VARIABLE, "").strip() or None


def requested_shard() -> tuple[int, int] | None:
    """
    The shard that SMARTER_TEST_SHARD asks for, if any.

    :returns: ``(shard, shards)``, counting from 1, or None to run the whole suite.
    :raises ValueError: if the value isn't ``<shard>/<shards>`` with ``1 <= shard <= shards``.
    """
    value = os.environ.get(SHARD_ENVIRONMENT_VARIABLE, "").strip()
    if not value:
        return None
    try:
        shard, shards = (int(part) for part in value.split("/"))
    except ValueError as e:
        raise ValueError(f"{SHARD_ENVIRONMENT_VARIABLE} must be <shard>/<shards>, e.g. 2/8, not {value!r}") from e
    if not 1 <= shard <= shards:
        raise ValueError(f"{SHARD_ENVIRONMENT_VARIABLE} must have 1 <= shard <= shards, not {value!r}")
    return shard, shards


def testcase_class_name(test: unittest.TestCase) -> str:
    """
    The dotted name of a test's TestCase class, e.g. ``smarter.lib.tests.test_json.TestJson``.

    :param test: a test.
    :returns: the module and qualified name of its class.
    """
    cls = type(test)
    return f"{cls.__module__}.{cls.__qualname__}"


def shard_tests(tests: list[unittest.TestCase], shard: int, shards: int) -> list[unittest.TestCase]:
    """
    The tests of one shard, in their original order.

    A TestCase is never split, because its ``setUpClass`` builds the fixtures that all of its
    tests share. TestCases are dealt out largest first, each to the shard with the fewest tests
    so far, and ties are broken by name, so the result depends only on the tests themselves.

    :param tests: the whole suite, as every shard discovers it.
    :param shard: the shard to return, counting from 1.
    :param shards: the number of shards.
    :returns: the tests of that shard.
    """
    sizes = collections.Counter(testcase_class_name(test) for test in tests)
    loads = [0] * shards
    shard_of: dict[str, int] = {}
    for name, size in sorted(sizes.items(), key=lambda item: (-item[1], item[0])):
        index = loads.index(min(loads))
        shard_of[name] = index + 1
        loads[index] += size
    return [test for test in tests if shard_of[testcase_class_name(test)] == shard]


class SmarterTestRunner(DiscoverRunner):
    """
    Django's test runner, except that it skips the infrastructure tests unless they are asked for,.

    writes a JUnit XML report when :data:`JUNIT_XML_ENVIRONMENT_VARIABLE` names a file, and runs
    only one shard of the suite when :data:`SHARD_ENVIRONMENT_VARIABLE` asks for one.
    """

    def __init__(self, *args, tags=None, exclude_tags=None, **kwargs):
        tags = set(tags or [])
        exclude_tags = set(exclude_tags or [])
        self.skipping_infrastructure = INFRASTRUCTURE not in tags and not include_infrastructure()
        if self.skipping_infrastructure:
            exclude_tags.add(INFRASTRUCTURE)
        super().__init__(*args, tags=tags or None, exclude_tags=exclude_tags, **kwargs)

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        if self.skipping_infrastructure and self.verbosity > 0:
            print(
                f"Skipping the tests tagged '{INFRASTRUCTURE}', which use real Kubernetes and AWS. "
                f"Run them with --tag {INFRASTRUCTURE}, or all tests with {ENVIRONMENT_VARIABLE}=true."
            )

    def build_suite(self, test_labels=None, **kwargs):
        """
        Build the suite as Django does, then keep only this run's shard, if one is asked for.

        :param test_labels: the test labels from the command line.
        :returns: the test suite.
        :raises ValueError: if a shard is asked for together with ``--parallel``.
        """
        suite = super().build_suite(test_labels, **kwargs)
        shard = requested_shard()
        if shard is None:
            return suite
        if isinstance(suite, self.parallel_test_suite):
            raise ValueError(f"{SHARD_ENVIRONMENT_VARIABLE} can't be combined with --parallel.")
        tests = list(iter_test_cases(suite))
        selected = shard_tests(tests, *shard)
        self.log(f"Running shard {shard[0]} of {shard[1]}: {len(selected)} of {len(tests)} test(s).")
        return self.test_suite(selected)

    def get_test_runner_kwargs(self):
        """
        Django's runner arguments, without a result class when a JUnit XML report is asked for.

        xmlrunner records the results with its own result class, which writes the report.
        Django's --debug-sql and --pdb result classes don't apply then.

        :returns: the keyword arguments of the unittest runner.
        """
        kwargs = super().get_test_runner_kwargs()
        if junit_xml_path() is not None:
            kwargs["resultclass"] = None
        return kwargs

    def run_suite(self, suite, **kwargs):
        """
        Run the suite, with xmlrunner instead of unittest's text runner when a JUnit XML report is asked for.

        xmlrunner still prints the usual progress and summary to the console.

        :param suite: the test suite to run.
        :returns: the test result.
        """
        path = junit_xml_path()
        if path is None:
            return super().run_suite(suite, **kwargs)

        import xmlrunner  # pylint: disable=import-outside-toplevel

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as output:
            self.test_runner = functools.partial(xmlrunner.XMLTestRunner, output=output)
            try:
                return super().run_suite(suite, **kwargs)
            finally:
                del self.test_runner


__all__ = [
    "ENVIRONMENT_VARIABLE",
    "INFRASTRUCTURE",
    "JUNIT_XML_ENVIRONMENT_VARIABLE",
    "SHARD_ENVIRONMENT_VARIABLE",
    "SmarterTestRunner",
    "include_infrastructure",
    "junit_xml_path",
    "requested_shard",
    "shard_tests",
    "testcase_class_name",
]
