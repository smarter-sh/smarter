Python
=========

With only a few exceptions, Smarter Framework is implemented in Python. There are certain conventions and
best practices that we've adopted, and want to impress upon future contributors to the project.

Coding Style
--------------

- Smarter Framework follows the `PEP 8 -- Style Guide for Python Code <https://peps.python.org/pep-0008/>`__.
- Smarter Framework uses `Black <https://black.readthedocs.io/en/stable/>`__ as its code formatter.
- `isort <https://pycqa.github.io/isort/>`__ to sort imports.
- `flake8 <https://flake8.pycqa.org/en/latest/>`__ for linting.
- `flake8-coding <https://pypi.org/project/flake8-coding/>`__ for coding style linting.
- `pylint <https://pylint.pycqa.org/en/latest/>`__ for code linting.
- `pylint-django <https://pypi.org/project/pylint-django/>`__ for Django-specific linting.
- `mypy <https://mypy.readthedocs.io/en/stable/>`__ for static type checking.
- `pyupgrade <https://github.com/asottile/pyupgrade>`__ to automatically upgrade syntax for newer Python versions.
- `codespell <https://github.com/codespell-project/codespell>`__ to check for spelling errors.
- `bandit <https://bandit.readthedocs.io/en/latest/>`__ for security linting.
- `coverage <https://coverage.readthedocs.io/en/latest/>`__ to measure test coverage.
- `pydocstringformatter <https://pypi.org/project/pydocstringformatter/>`__ to format docstrings.
- `pre-commit <https://pre-commit.com/>`__ for managing git hooks.
- `tox <https://tox.readthedocs.io/en/latest/>`__ for testing in multiple environments.
- `watchdog <https://python-watchdog.readthedocs.io/en/stable/>`__ for file system monitoring.
- `pre-commit hooks <https://pre-commit.com/>`__ for additional checks, such as fixing byte order markers, checking for merge conflicts, trailing whitespace, and more.


Type Hinting
--------------

Smarter Framework uses Python type hinting extensively throughout the codebase. This helps improve code readability,
provides better support for IDEs, and enables static type checking with tools like mypy.

- `pandas-stubs <https://github.com/VirtusLab/pandas-stubs>`__ for pandas type annotations.
- `types-cachetools <https://pypi.org/project/types-cachetools/>`__ for cachetools type annotations.
- `types-lxml <https://pypi.org/project/types-lxml/>`__ for lxml type annotations.
- `types-Markdown <https://pypi.org/project/types-Markdown/>`__ for Markdown type annotations.
- `types-paramiko <https://pypi.org/project/types-paramiko/>`__ for paramiko type annotations.
- `types-PyYAML <https://pypi.org/project/types-PyYAML/>`__ for PyYAML type annotations.
- `types-requests <https://pypi.org/project/types-requests/>`__ for requests type annotations.
- `django-stubs <https://github.com/typeddjango/django-stubs>`__ for Django type annotations.
- `djangorestframework-stubs <https://github.com/typeddjango/djangorestframework-stubs>`__ for Django REST Framework type annotations.
- `mypy_extensions <https://pypi.org/project/mypy-extensions/>`__ for additional type annotation utilities.

Dependencies
--------------

Smarter Framework relies on a number of third-party Python packages to provide various functionalities.
These are maintained in the `smarter/requirements/in` directory of the project, with separate
files for different environments and use cases.

.. toctree::
   :maxdepth: 1
   :caption: Smarter Framework Python Requirements

   python/base
   python/constraints
   python/docker
   python/local
