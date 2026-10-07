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
"""

import os

from django.test.runner import DiscoverRunner

INFRASTRUCTURE = "infrastructure"
"""The tag of tests that use real infrastructure: Kubernetes, AWS Route53, ACM, and so on."""
ENVIRONMENT_VARIABLE = "SMARTER_TEST_INFRASTRUCTURE"


def include_infrastructure() -> bool:
    """Whether SMARTER_TEST_INFRASTRUCTURE asks for the infrastructure tests to run too."""
    return os.environ.get(ENVIRONMENT_VARIABLE, "").strip().lower() in ("1", "true", "yes")


class SmarterTestRunner(DiscoverRunner):
    """Django's test runner, except that it skips the infrastructure tests unless they are asked for."""

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


__all__ = ["ENVIRONMENT_VARIABLE", "INFRASTRUCTURE", "SmarterTestRunner", "include_infrastructure"]
