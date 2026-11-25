# Python Requirements

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)](https://www.python.org/)
[![PyPI](https://img.shields.io/badge/PyPI-website-blue?logo=pypi)](https://pypi.org/)

Python requirements files are managed here. These files are formatted for use with the
`pip` (Python Install Package) software utility during the Docker build procedure.
The packages themselves are distributed from [pypi](https://pypi.org/). You can review
salient details for any package by searching for it on the pypi.org web site. Each package
also has its own unique url. For example, you can review the Django pypi package at
[https://pypi.org/project/Django/](https://pypi.org/project/Django/)

The Dockerfile in the root of this project consumes and processes the `docker.txt` as part
of its normal build process. When running locally, it will also process `local.txt`, which
contains additional software linting and code quality tools which are not germane to running
in production.

Ultimately, regardless of environment, the Dockerfile will create a Python Virtual Environment
inside of the container that will serve the python executable interpreter with all third
party software packages.

**DO NOT EDIT THESE FILES.**

A maintainer updates them with `make python-requirements`, which runs pip-compile on each
`.in` file in the `in/` subfolder, then `make python-hashes` and `make python-cooldown`. Dependabot doesn't manage them:
its changes to these lockfiles left pip unable to install them. Further instructions are included
in the header docs of each `.in` file.

Each lockfile pins every package, direct and transitive, to an exact version, with the sha256 of
each of its files (`make python-hashes`). The Docker build installs them with `--require-hashes`, so
it fails on a file it hasn't seen before. A lockfile written without hashes fails the build too:
always regenerate them with `make python-requirements`.

- `make python-cooldown` fails when a lockfile pins a release uploaded to PyPI in the last 14 days.
- `make python-audit` fails when one pins a release with a published vulnerability. The Tests
  workflow runs it on every pull request to main.

See [Supply-Chain Security](https://docs.smarter.sh/smarter-platform/system-administration/security/supply-chain.html).

## Updating the requirements files

From the root of this project:

```console
make python-requirements                                   # keep the pins, e.g. after editing an .in file
make python-requirements PYTHON_COOLDOWN_ALLOW="package"   # a security fix newer than 14 days
```

It runs pip-compile with `--allow-unsafe` (pip and setuptools are pinned too, because
`--require-hashes` refuses a dependency without a hash), then `make python-hashes` and
`make python-cooldown` (`scripts/python_lockfiles.py`). Don't run pip-compile by itself: it writes
the lockfile without hashes, and the Docker build then fails.
