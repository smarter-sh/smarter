Unit Testing
============

Smarter takes code quality and testing seriously. As of version 0.16 there are 2,900 tests in
the test suite. Pull requests must pass all tests before they can be merged. Moreover,
code coverage is monitored on pull requests to ensure that new code is adequately tested. While 100% coverage is not
patently unrealistic for this project, we strive to maintain high coverage across the codebase. In parts of the
codebase that we consider 'core', we aim for at least 90% coverage.

Try to the guidelines below to help ensure that your tests provide maximum value with minimum effort on your part.
We've invested heavily in unit test infrastructure by way of bases classes, mixins, and fixtures to make writing tests as easy
as possible.

.. note::

  *Please be aware that the principal author generously awards himself a self-assessment of "C-" for test writing skills.
  So, please be kind when reviewing the legacy testing infrastructure.*

Local Testing
-----------------

To run the test suite locally, use the following command from the project root:

.. code-block:: console

  docker exec smarter-app bash -c "python manage.py test smarter"

  # or, to run tests for a specific app
  docker exec smarter-app bash -c "python manage.py test smarter.apps.account"

  # or
  make test

Infrastructure Tests
--------------------

Some tests use real infrastructure: they deploy LLMClients to the Kubernetes cluster, and create
DNS records and TLS certificates in AWS. They are slow, e.g. a deploy waits up to 40 minutes for a
certificate that a local cluster never issues, and they need live credentials. They are tagged
``infrastructure``, and skipped unless they are asked for:

.. code-block:: console

  python manage.py test                                    # everything else
  python manage.py test --tag infrastructure               # only the infrastructure tests
  SMARTER_TEST_INFRASTRUCTURE=true python manage.py test   # everything

Tag a test, or a whole TestCase, that uses real infrastructure, with
:mod:`smarter.lib.unittest.runner`'s ``INFRASTRUCTURE`` tag:

.. code-block:: python

  from django.test import tag
  from smarter.lib.unittest.runner import INFRASTRUCTURE

  @tag(INFRASTRUCTURE)
  class TestDeploy(TestAccountMixin):
      ...

Prefer a fake, though: the LLMHost and Vectorstore tests replace the cluster with an in-memory
backend, so that they test the same code in seconds.

Coverage Report
-----------------

To generate a code coverage report, use the following command from the project root:

.. code-block:: console

  docker exec smarter-app bash -c "coverage run manage.py test && coverage report -m && coverage html"

  # or
  make coverage

Conventions
-----------

unittest
~~~~~~~~~~~~~~~~~~

Smarter uses the built-in :mod:`unittest <unittest>` framework for unit tests. All tests should be placed
in a ``tests`` subpackage within the app being tested. Test modules should be named with the ``test_*.py``
pattern. Test case classes should be named with the ``*TestCase`` suffix. Individual test methods should be named
with the ``test_*`` prefix.

Try to keep tests nearby the code they are testing to make it easier to find and maintain them and to minimize the
the number of individual test files any any given directory.

data files
~~~~~~~~~~~~~~~~~~

Test data files should be placed in a ``data`` subdirectory nearby the ``tests`` package of the app being tested.


SmarterTestBase
~~~~~~~~~~~~~~~~~~

All unit tests should inherit from :class:`SmarterTestBase <smarter.lib.unittest.base_classes.SmarterTestBase>`,
or from a subclass thereof. This base class provides a number of useful features, including functions
for reading test data files in various formats in a read-only manner, generating unique identifiers and hash suffixes.

.. code-block:: python

  from smarter.lib.unittest.base_classes import SmarterTestBase


TestAccountMixin
~~~~~~~~~~~~~~~~~~

This mixin inherits from :class:`SmarterTestBase <smarter.lib.unittest.base_classes.SmarterTestBase>`
and provides additional supporting functionality for tests that involve user accounts, such as creating test users
and logging them in and setting up various roles and permissions. This class does a reasonably good job of
cleaning up after itself, deleting any test users it creates, regardless of whether tests pass or fail.

.. code-block:: python

  from smarter.apps.account.tests.mixins import TestAccountMixin


Code Quality
~~~~~~~~~~~~~~~~~~

The project uses automated code-quality checks to keep the code clean, consistent, readable, and safe.
Before code is committed, pre-commit checks automatically format Python and JavaScript code, organize
imports, remove unused imports, improve Python syntax, and keep documentation comments consistent. It
also checks for common mistakes such as spelling errors, trailing whitespace, invalid JSON/YAML/XML/TOML,
merge conflicts, broken links, accidental credentials or private keys, debug statements, and other
repository problems. Python code is checked for style and potential security issues, while JavaScript
code is checked with ESLint and formatting tools. Commit messages are also checked to keep them consistent.
Many of these checks can automatically fix simple problems, and pre-commit.ci runs the checks in the
background and can create automatic fixes, helping ensure that every contribution meets the project’s
basic standards before it becomes part of the codebase.
