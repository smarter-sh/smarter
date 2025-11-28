Developer Guidelines
====================

Please make an effort to follow these guidelines when contributing code to
this project. They’re designed to help ensure that the code remains of
high quality, that it's easy to read, and that it's maintainable over time.

Unit Testing
------------

This project includes an extensive collection of Python unit tests for
verifying both the cloud infrastructure, its configuration, and of
course, the Python code itself. As of Feb-2024 there are nearly 70 unit
tests incorporated into the automated CI-CD processes (see below). In
accordance with Python best practice, this project uses
`coverage <https://pypi.org/project/coverage/>`__ to gauge the overall
effectiveness of these tests.

Pydantic
--------

Originally created in 2017,
`Pydantic <https://docs.pydantic.dev/latest/>`__ has become the most
widely used data validation library for Python. It is especially useful
for data driven applications like this one, involving frequent
integrations with a variety of cloud infrastructure services in a
variety of environments, configured by a variety of different possible
sources of data including environment variables, .env file,
terraform.tfvars and system constants. We use it for the
`Settings https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/common/conf.py`__ class in this
project, and also for validating yaml
`manifests <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/manifest>`__ for the OpenAI Function
Calling feature. It’s an important addition because it enforces strong
type and business rule validation checking of all of the configuration
parameters for the AWS Lambdas, and it ensures that nothing ever changes
these values at run-time once they’ve been set. And this in turn is
important because erroneous automation code could otherwise lead to some
wildly disastrous results. 😳

Automations
-----------

We leverage automations using Github Actions, third party services,
make, bash and anything else that might become freely available to the
project in future. As a community-supported code project, automations
are important for minimizing the effort required by our committers to
keep this code shippable. But it’s also an important component of our
strategy for maintaining high quality standards. Automations give us the
ability to do more work, more consistently, and with less effort.

Of note:

- `Automated Pull
  Requests <https://github.com/smarter-sh/smarter/pulls?q=is%3Apr+is%3Aclosed>`__:
  Github Actions are triggered on pull requests to run any of several
  different kinds of technology-specific unit tests depending on the
  contents of the commits included in the PR.
- `python-dotenv <https://github.com/smarter-sh/smarter/blob/main/docs/example-dot-env>`__ for
  storing sensitive data for local development
- `.gitignore <https://github.com/smarter-sh/smarter/blob/main/.gitignore>`__ ensures that no sensitive nor useless
  data accidentally gets pushed to GitHub.
- `tox.ini <https://github.com/smarter-sh/smarter/blob/main/tox.ini>`__ file for configuring behaviors of Python
  testing tools
- `GitHub Actions <https://github.com/features/actions>`__ automates
  unit testing, semantic release rule checking, and dependabot actions.
- `GitHub
  Secrets <https://github.com/smarter-sh/smarter/settings/secrets/actions>`__
  to provide sensitive data to Github Actions workflows
- `GitHub Issues <https://github.com/features/issues>`__
- `Makefile <https://github.com/smarter-sh/smarter/blob/main/Makefile>`__ automates procedures like init, build, test,
  release and linting for Python, ReactJS and Terraform.
- `pre-commit <https://pre-commit.com/>`__ automatically enforces a
  multitude of code quality, coding style and security policies.
- `Dependabot <https://github.com/dependabot>`__ automatically updates
  the version pins of code library dependencies for Python, ReactJS and
  Terraform.
- `Unit Tests <https://docs.pytest.org/>`__ are automated and can be invoked

  - manually from the command line
  - manually from GitHub Actions
  - automatically by Dependabot.

- `Mergify <https://mergify.com/>`__ automates processing of bot-created
  pull requests
- `Semantic
  Release <https://github.com/semantic-release/semantic-release>`__
  automates version releases as well as maintains the change log for the
  repo.
- `Change Log <http://keepachangelog.com/>`__

Linters and Formatters
----------------------

Linters and formatters are tools used in programming to analyze and
improve the quality of code. This project leverages several, including:

Code Formatting
~~~~~~~~~~~~~~~

- `Prettier <https://prettier.io/>`__: an opinionated code formatter
  that supports many file formats and languages. This project leverages
  Prettier to standardize formatting of md, css, json, yml, js, jsx and
  Typescript files.
- `Black <https://github.com/psf/black>`__: an opinionated code
  formatter for Python which is compatible with `PEP
  8 <https://peps.python.org/pep-0008/>`__ and the `Python Style
  Guide <https://www.python.org/docs/essays/styleguide/>`__.
- `isort <https://pycqa.github.io/isort/>`__: a Python utility that
  sorts imports alphabetically, and automatically, separated into
  sections and by type.

Code Analysis
~~~~~~~~~~~~~

- `ESLint <https://eslint.org/>`__: an open source project that helps
  you find and fix problems with your JavaScript and JSX code.
- `Flake8 <https://flake8.pycqa.org/en/latest/>`__: provides Python
  syntax checking, naming style enforcement, code style enforcement, and
  `cyclomatic
  complexity <https://en.wikipedia.org/wiki/Cyclomatic_complexity>`__
  analysis.
- `pylint <https://pypi.org/project/pylint/>`__: a static code analyser
  for Python. It analyses your code without actually running it. It
  checks for errors, enforces a coding standard, looks for code smells,
  and can make suggestions about how the code could be refactored.
- `bandit <https://github.com/PyCQA/bandit>`__: a tool designed to find
  common security issues in Python code.

Pre-commit hooks
~~~~~~~~~~~~~~~~

- `pre-commit Hooks <https://pre-commit.com/hooks.html>`__: scripts that
  run automatically before each commit is made to a repository, checking
  your code for embedded passwords, errors, issues, and any of a
  multitude of configurable policies that you can optionally enforce.
  They’re part of the git hooks system, which allows you to trigger
  actions at certain points in git’s execution. This project uses many
  Hooks. See `pre-commit-config.yaml <https://github.com/smarter-sh/smarter/blob/main/.pre-commit-config.yaml#L11>`__.
- `codespell <https://github.com/codespell-project/codespell>`__: fixes
  common misspellings in text files. It’s designed primarily for
  checking misspelled words in source code, but it can be used with
  other files as well.
