# Python Requirements

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/<package-name>.svg?logo=pypi)](https://pypi.org/project/<package-name>/)

Python requirements files are managed here. These files are formatted for use with the
`pip` (Python Install Package) software utility. The packages themselves are distributed
from [pypi](https://pypi.org/).

The Dockerfile in the root of this project consumes and processes the `docker.txt` as part
of its normal build process. When running locally, it will also process `local.txt`, which
contains additional software linting and code quality tools which are not germane to running
in production.

**DO NOT EDIT THESE FILES.**

Python requirements for this project are maintained automatically via GitHub's Dependabot service,
combined with automated ci-cd procedures that occasionally re-generated these .txt files
from the .in files located in the .in subfolder. Further instructions are included the header docs
of each .in file.

## Manually updating requirements files

You can manually run pip-compile from the root of this project, as follows:

```console
pip-compile smarter/requirements/in/base.in -o smarter/requirements/base.txt
pip-compile smarter/requirements/in/docker.in -o smarter/requirements/docker.txt
pip-compile smarter/requirements/in/local.in -o smarter/requirements/local.txt
```
