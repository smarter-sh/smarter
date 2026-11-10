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

Tests that send real requests to LLM providers, to find what each vendor's models accept, are
tagged :data:`VENDOR`. They cost a little money, so they are skipped the same way:

.. code-block:: console

    python manage.py test --tag vendor               # only the vendor tests
    SMARTER_TEST_VENDOR=true python manage.py test   # everything, with the vendor tests

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
import os
import unittest

from django.test.runner import DiscoverRunner
from django.test.utils import (  # type: ignore[attr-defined]  # django-stubs doesn't declare iter_test_cases; pyright: ignore[reportAttributeAccessIssue]
    iter_test_cases,
)

INFRASTRUCTURE = "infrastructure"
"""The tag of tests that use real infrastructure: Kubernetes, AWS Route53, ACM, and so on."""
ENVIRONMENT_VARIABLE = "SMARTER_TEST_INFRASTRUCTURE"
"""The environment variable that, set to ``true``, ``yes`` or ``1``, runs the infrastructure tests too."""
VENDOR = "vendor"
"""The tag of tests that send real, billed requests to LLM providers, e.g. to probe what OpenAI's models accept."""
VENDOR_ENVIRONMENT_VARIABLE = "SMARTER_TEST_VENDOR"
"""The environment variable that, set to ``true``, ``yes`` or ``1``, runs the vendor tests too."""
OPT_IN_TAGS: dict[str, str] = {
    INFRASTRUCTURE: ENVIRONMENT_VARIABLE,
    VENDOR: VENDOR_ENVIRONMENT_VARIABLE,
}
"""The tags that are skipped unless they are asked for, and the environment variable that asks for each."""
OPT_IN_TAG_DESCRIPTIONS: dict[str, str] = {
    INFRASTRUCTURE: "use real Kubernetes and AWS",
    VENDOR: "send real, billed requests to LLM providers",
}
JUNIT_XML_ENVIRONMENT_VARIABLE = "SMARTER_TEST_JUNIT_XML"
"""The environment variable that names the file to write a JUnit XML report of the test results to."""
SHARD_ENVIRONMENT_VARIABLE = "SMARTER_TEST_SHARD"
"""The environment variable that picks the part of the suite to run, as ``<shard>/<shards>``, e.g. ``2/8``."""


def include_tag(tag: str) -> bool:
    """
    Return whether an opt-in tag's environment variable, in :data:`OPT_IN_TAGS`, asks for its tests to run too.

    :param tag: An opt-in tag, e.g. :data:`VENDOR`.
    :returns: True if the variable is ``1``, ``true`` or ``yes``, in any case.
    """
    variable = OPT_IN_TAGS[tag]
    value = os.environ.get(variable, "")
    normalized_value = value.strip().lower()
    included = normalized_value in ("1", "true", "yes")
    return included


def include_infrastructure() -> bool:
    """
    Return whether ``SMARTER_TEST_INFRASTRUCTURE`` asks for the infrastructure tests to run too.

    :returns: True if the variable is ``1``, ``true`` or ``yes``, in any case.
    """
    included = include_tag(INFRASTRUCTURE)
    return included


def junit_xml_path() -> str | None:
    """
    Return the file that ``SMARTER_TEST_JUNIT_XML`` asks for a JUnit XML report to be written to, if any.

    :returns: The file's path, or None if the variable is unset or blank.
    """
    value = os.environ.get(JUNIT_XML_ENVIRONMENT_VARIABLE, "")
    path = value.strip()
    if not path:
        return None
    return path


def requested_shard() -> tuple[int, int] | None:
    """
    Return the shard that ``SMARTER_TEST_SHARD`` asks for, if any.

    :returns: ``(shard, shards)``, counting from 1, or None to run the whole suite.
    :raises ValueError: If the value isn't ``<shard>/<shards>`` with ``1 <= shard <= shards``.
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
    Return the dotted name of a test's TestCase class, e.g. ``smarter.lib.tests.test_json.TestJson``.

    :param test: A test.
    :returns: The module and qualified name of its class.
    """
    cls = type(test)
    name = f"{cls.__module__}.{cls.__qualname__}"
    return name


def shard_tests(tests: list[unittest.TestCase], shard: int, shards: int) -> list[unittest.TestCase]:
    """
    Return the tests of one shard, in their original order.

    A TestCase is never split, because its ``setUpClass`` builds the fixtures that all of its
    tests share. TestCases are dealt out largest first, each to the shard with the fewest tests
    so far, and ties are broken by name, so the result depends only on the tests themselves.

    :param tests: The whole suite, as every shard discovers it.
    :param shard: The shard to return, counting from 1.
    :param shards: The number of shards.
    :returns: The tests of that shard.
    """
    sizes = collections.Counter(testcase_class_name(test) for test in tests)
    loads = [0] * shards
    shard_of: dict[str, int] = {}
    for name, size in sorted(sizes.items(), key=lambda item: (-item[1], item[0])):
        index = loads.index(min(loads))
        shard_of[name] = index + 1
        loads[index] += size
    selected = []
    for test in tests:
        test_shard = shard_of[testcase_class_name(test)]
        if test_shard == shard:
            selected.append(test)
    return selected


class SmarterTestRunner(DiscoverRunner):
    """
    Django's test runner, with three additions for Smarter's suite.

    It skips the infrastructure and vendor tests unless they are asked for, writes a JUnit XML report when
    :data:`JUNIT_XML_ENVIRONMENT_VARIABLE` names a file, and runs only one shard of the suite
    when :data:`SHARD_ENVIRONMENT_VARIABLE` asks for one.
    """

    def __init__(self, *args, tags: list[str] | None = None, exclude_tags: list[str] | None = None, **kwargs):
        """
        Create the runner, excluding each tag of :data:`OPT_IN_TAGS` unless its tests are asked for.

        They are asked for by ``--tag <tag>``, e.g. ``--tag infrastructure``, or by the tag's
        environment variable, e.g. :data:`ENVIRONMENT_VARIABLE`.

        :param args: Passed to Django's ``DiscoverRunner``.
        :param tags: The tags to run, from ``--tag``.
        :param exclude_tags: The tags to skip, from ``--exclude-tag``.
        :param kwargs: Passed to Django's ``DiscoverRunner``.
        """
        tags = list(tags or [])
        exclude_tags = list(exclude_tags or [])
        self.skipped_tags: list[str] = []
        for tag in OPT_IN_TAGS:
            if tag in tags:
                continue
            if include_tag(tag):
                continue
            self.skipped_tags.append(tag)
            if tag not in exclude_tags:
                exclude_tags.append(tag)
        self.skipping_infrastructure = INFRASTRUCTURE in self.skipped_tags
        runner_tags = None
        if tags:
            runner_tags = tags
        # as keywords after any positional arguments, which DiscoverRunner takes in another order
        kwargs["tags"] = runner_tags
        kwargs["exclude_tags"] = exclude_tags
        super().__init__(*args, **kwargs)

    def setup_test_environment(self, **kwargs):
        """
        Set up Django's test environment, and say which opt-in tests are skipped.

        :param kwargs: Passed to Django's ``setup_test_environment()``.
        """
        super().setup_test_environment(**kwargs)
        if self.verbosity <= 0:
            return
        for tag in self.skipped_tags:
            description = OPT_IN_TAG_DESCRIPTIONS[tag]
            variable = OPT_IN_TAGS[tag]
            print(
                f"Skipping the tests tagged '{tag}', which {description}. "
                f"Run them with --tag {tag}, or all tests with {variable}=true."
            )

    def build_suite(self, test_labels=None, **kwargs):
        """
        Build the suite as Django does, then keep only this run's shard, if one is asked for.

        :param test_labels: The test labels from the command line.
        :param kwargs: Passed to Django's ``build_suite()``.
        :returns: The test suite.
        :raises ValueError: If a shard is asked for together with ``--parallel``.
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
        Return Django's runner arguments, without a result class when a JUnit XML report is asked for.

        xmlrunner records the results with its own result class, which writes the report.
        Django's --debug-sql and --pdb result classes don't apply then.

        :returns: The keyword arguments of the unittest runner.
        """
        kwargs = super().get_test_runner_kwargs()
        if junit_xml_path() is not None:
            kwargs["resultclass"] = None
        return kwargs

    def run_suite(self, suite, **kwargs):
        """
        Run the suite, with xmlrunner instead of unittest's text runner when a JUnit XML report is asked for.

        xmlrunner still prints the usual progress and summary to the console.

        :param suite: The test suite to run.
        :param kwargs: Passed to Django's ``run_suite()``.
        :returns: The test result.
        """
        path = junit_xml_path()
        if path is None:
            return super().run_suite(suite, **kwargs)

        import xmlrunner  # pylint: disable=import-outside-toplevel

        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as output:
            # A subclass that binds the output file, rather than functools.partial,
            # because DiscoverRunner.test_runner is typed as a TextTestRunner class.
            class XMLTestRunner(xmlrunner.XMLTestRunner):
                """Xmlrunner's runner, writing its report to the open file."""

                def __init__(self, **runner_kwargs):
                    # xmlrunner annotates output as str, a directory of one report per
                    # TestCase, but also takes an open file, for one combined report.
                    super().__init__(output=output, **runner_kwargs)  # pyright: ignore[reportArgumentType]

            self.test_runner = XMLTestRunner
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
