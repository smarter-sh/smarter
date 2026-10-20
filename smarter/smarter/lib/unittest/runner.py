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
"""

import functools
import os

from django.test.runner import DiscoverRunner

INFRASTRUCTURE = "infrastructure"
"""The tag of tests that use real infrastructure: Kubernetes, AWS Route53, ACM, and so on."""
ENVIRONMENT_VARIABLE = "SMARTER_TEST_INFRASTRUCTURE"
JUNIT_XML_ENVIRONMENT_VARIABLE = "SMARTER_TEST_JUNIT_XML"
"""The environment variable that names the file to write a JUnit XML report of the test results to."""


def include_infrastructure() -> bool:
    """Whether SMARTER_TEST_INFRASTRUCTURE asks for the infrastructure tests to run too."""
    return os.environ.get(ENVIRONMENT_VARIABLE, "").strip().lower() in ("1", "true", "yes")


def junit_xml_path() -> str | None:
    """The file that SMARTER_TEST_JUNIT_XML asks for a JUnit XML report to be written to, if any."""
    return os.environ.get(JUNIT_XML_ENVIRONMENT_VARIABLE, "").strip() or None


class SmarterTestRunner(DiscoverRunner):
    """
    Django's test runner, except that it skips the infrastructure tests unless they are asked for,.

    and writes a JUnit XML report when :data:`JUNIT_XML_ENVIRONMENT_VARIABLE` names a file.
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
    "SmarterTestRunner",
    "include_infrastructure",
    "junit_xml_path",
]
