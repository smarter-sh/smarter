# Python Requirements

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
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

Python requirements for this project are maintained automatically via GitHub's Dependabot service,
combined with automated ci-cd procedures that occasionally re-generate these .txt files
from the .in files located in the .in subfolder. Further instructions are included the header docs
of each .in file.

## Manually updating requirements files

You can manually run pip-compile from the root of this project, as follows:

```console
pip-compile smarter/requirements/in/base.in -o smarter/requirements/base.txt
pip-compile smarter/requirements/in/docker.in -o smarter/requirements/docker.txt
pip-compile smarter/requirements/in/local.in -o smarter/requirements/local.txt
```
