"""
The scripts of a repository that ``manage.py load_from_github`` loads.

A repository of Smarter manifests may also hold scripts that set up what its manifests need but
can't declare, e.g. the database that a SqlConnection connects to. The Stackademy project,
https://github.com/smarter-sh/stackademy, is the reference: its ``scripts/create-course-database.sh``
creates the course database that its SqlConnection and SqlPlugin use.

The scheme
----------

- **The scripts folder.** A repository's scripts are in its top-level ``scripts/`` folder,
  :data:`SCRIPTS_FOLDER`. ``load_from_github`` never looks for manifests there.
- **The configuration file.** ``scripts/scripts.yaml``, :data:`SCRIPTS_CONFIG`, lists the scripts to
  run, and when. Only the scripts that it lists are run, so the folder may also hold the files that
  they read, e.g. a SQL file. Its model is :class:`RepositoryScriptsConfig`:

  .. code-block:: yaml

      scripts:
        - path: create-course-database.sh   # relative to scripts/
          stage: pre                        # pre: before the manifests are applied. post: after.
          description: Create the course database that the SqlConnection connects to.
          args: []                          # optional: the script's arguments
          timeout: 300                      # optional: the seconds that it may run, at most 3600

- **The stages.** ``pre`` scripts run before any manifest is applied, so that what the manifests
  name exists when they are applied, e.g. a database. ``post`` scripts run after every manifest is
  applied, and the LLMClients deployed, e.g. to seed data through the platform's api. Within a
  stage, the scripts run in the order of the configuration file.
- **How a script runs.** As an executable, with its own shebang line (so it must be committed with
  its executable bit set), in the repository's root folder, with the ``args`` of its configuration.
- **What a script receives.** Only the environment of :func:`script_environment`, never the
  platform's own: a repository's script never sees the platform's cloud or LLM provider
  credentials. The database server's administrator is included, because creating a database and
  its users is what a ``pre`` script typically does.
- **Failures.** A script that fails, i.e. exits non-zero, or runs out of time, doesn't stop the
  manifests or the other scripts. ``load_from_github`` fails at the end, with the list of what
  failed. A configuration file that is not valid fails ``load_from_github`` before anything runs.
- **Opt in.** Scripts run only with ``load_from_github --run_scripts``, which only ``manage.py
  initialize_platform`` passes, because a ``pre`` script runs as the database server's
  administrator. ``manage.py initialize_account`` doesn't pass it, so a platform's shared
  database is created once, rather than for each account.
"""

import os
import subprocess
import time
from typing import Literal, Optional

import yaml
from django.conf import settings
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

SCRIPTS_FOLDER = "scripts"
"""A repository's scripts folder, at its root.

``load_from_github`` finds no manifests in it.
"""

SCRIPTS_CONFIG = "scripts.yaml"
"""The scripts folder's configuration file, :class:`RepositoryScriptsConfig`."""

SCRIPT_DEFAULT_TIMEOUT = 300
"""The seconds that a script may run, unless its configuration says otherwise."""

SCRIPT_MAX_TIMEOUT = 3600
"""The most seconds that a script's configuration may give it."""

SCRIPT_STAGE_PRE = "pre"
"""The stage of the scripts that run before any manifest is applied."""

SCRIPT_STAGE_POST = "post"
"""The stage of the scripts that run after every manifest is applied, and the LLMClients deployed."""

ScriptStage = Literal["pre", "post"]
"""When a script runs: :data:`SCRIPT_STAGE_PRE` or :data:`SCRIPT_STAGE_POST`."""

SCRIPT_INHERITED_VARIABLES = ("PATH", "HOME", "LANG", "LC_ALL", "TZ")
"""The only variables of the platform's own environment that a script receives."""


class RepositoryScript(BaseModel):
    """One script of ``scripts/scripts.yaml``: which file, when it runs, and how."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(
        ...,
        description="The script's file, relative to the scripts folder, e.g. create-course-database.sh.",
        examples=["create-course-database.sh"],
    )
    stage: ScriptStage = Field(
        ...,
        description="pre: run before any manifest is applied. post: run after every manifest is applied.",
        examples=["pre"],
    )
    description: Optional[str] = Field(
        default=None, description="What the script does, for the people who read the configuration."
    )
    args: list[str] = Field(default_factory=list, description="The script's arguments.")
    timeout: int = Field(
        default=SCRIPT_DEFAULT_TIMEOUT,
        ge=1,
        le=SCRIPT_MAX_TIMEOUT,
        description=f"The seconds that the script may run, at most {SCRIPT_MAX_TIMEOUT}.",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """
        Validate that the path is a file name, or a relative path, inside the scripts folder.

        :param v: The path.
        :returns: The path, normalized.
        :raises ValueError: If it is empty, absolute, or leaves the scripts folder.
        """
        if not v or not v.strip():
            raise ValueError("path is required.")
        path = os.path.normpath(v.strip())
        if os.path.isabs(path) or path == ".." or path.startswith(".." + os.sep):
            raise ValueError(f"path {v} must be inside the {SCRIPTS_FOLDER} folder.")
        return path


class RepositoryScriptsConfig(BaseModel):
    """
    A repository's ``scripts/scripts.yaml``: the scripts that ``load_from_github --run_scripts`` runs.

    See the scheme in :mod:`smarter.apps.account.repository_scripts`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    scripts: list[RepositoryScript] = Field(default_factory=list, description="The scripts, in the order to run them.")

    def for_stage(self, stage: ScriptStage) -> list[RepositoryScript]:
        """
        Return the scripts of a stage, in the order of the configuration file.

        :param stage: :data:`SCRIPT_STAGE_PRE` or :data:`SCRIPT_STAGE_POST`.
        :returns: The stage's scripts.
        :rtype: list[RepositoryScript]
        """
        return [script for script in self.scripts if script.stage == stage]


def scripts_config_path(local_path: str) -> str:
    """
    Return the path of a repository's scripts configuration file, whether or not it exists.

    :param local_path: The repository's clone.
    :returns: ``<local_path>/scripts/scripts.yaml``.
    :rtype: str
    """
    return os.path.join(local_path, SCRIPTS_FOLDER, SCRIPTS_CONFIG)


def load_scripts_config(local_path: str) -> Optional[RepositoryScriptsConfig]:
    """
    Read and validate a repository's ``scripts/scripts.yaml``.

    :param local_path: The repository's clone.
    :returns: The configuration, or None if the repository has none.
    :rtype: Optional[RepositoryScriptsConfig]
    :raises SmarterValueError: If the file is not valid YAML, or not a valid configuration, or names a
        script that doesn't exist or isn't executable.
    """
    filespec = scripts_config_path(local_path)
    if not os.path.isfile(filespec):
        return None
    relative = os.path.join(SCRIPTS_FOLDER, SCRIPTS_CONFIG)
    try:
        with open(filespec, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = RepositoryScriptsConfig.model_validate(data)
    except (yaml.YAMLError, ValidationError) as e:
        raise SmarterValueError(f"{relative} is not valid: {e}") from e
    for script in config.scripts:
        script_path = os.path.join(local_path, SCRIPTS_FOLDER, script.path)
        if not os.path.isfile(script_path):
            raise SmarterValueError(f"{relative} names {script.path}, which is not in {SCRIPTS_FOLDER}/.")
        if not os.access(script_path, os.X_OK):
            raise SmarterValueError(
                f"{relative} names {script.path}, which is not executable. Commit it with its executable bit set."
            )
    return config


def script_environment(url: str, local_path: str, account_number: str, username: str) -> dict[str, str]:
    """
    Return the environment that a repository's script runs in, and nothing more.

    ===================================  ==================================================================
    Variable                             Value
    ===================================  ==================================================================
    ``SMARTER_REPOSITORY_URL``           The repository's url.
    ``SMARTER_REPOSITORY_ROOT``          The clone's folder, which is also the script's working folder.
    ``SMARTER_ACCOUNT_NUMBER``           The account that owns the repository's resources.
    ``SMARTER_USERNAME``                 The user that owns them.
    ``SMARTER_DATABASE_HOST``            The host of the platform's database server.
    ``SMARTER_DATABASE_PORT``            Its port.
    ``SMARTER_DATABASE_ADMIN_USERNAME``  Its administrator, ``smarter_settings.mysql_root_username``.
    ``MYSQL_PWD``                        The administrator's password, ``smarter_settings.mysql_root_password``,
                                         where the MariaDB and MySQL clients read it. Missing if it is not set.
    ===================================  ==================================================================

    Plus ``PATH``, ``HOME``, ``LANG``, ``LC_ALL`` and ``TZ`` from the platform's environment, if they
    are set, :data:`SCRIPT_INHERITED_VARIABLES`, and no other: a script never sees the platform's own
    credentials.

    :param url: The repository's url.
    :param local_path: The repository's clone.
    :param account_number: The account that owns the repository's resources.
    :param username: The user that owns them.
    :returns: The environment.
    :rtype: dict[str, str]
    """
    database = settings.DATABASES["default"]
    env = {name: os.environ[name] for name in SCRIPT_INHERITED_VARIABLES if name in os.environ}
    env.update(
        {
            "SMARTER_REPOSITORY_URL": url,
            "SMARTER_REPOSITORY_ROOT": local_path,
            "SMARTER_ACCOUNT_NUMBER": account_number,
            "SMARTER_USERNAME": username,
            "SMARTER_DATABASE_HOST": str(database.get("HOST") or "localhost"),
            "SMARTER_DATABASE_PORT": str(database.get("PORT") or 3306),
            "SMARTER_DATABASE_ADMIN_USERNAME": smarter_settings.mysql_root_username,
        }
    )
    if smarter_settings.mysql_root_password is not None:
        env["MYSQL_PWD"] = smarter_settings.mysql_root_password.get_secret_value()
    return env


def run_script(local_path: str, script: RepositoryScript, env: dict[str, str]) -> str:
    """
    Run one of a repository's scripts, in the repository's root folder, and log what it writes.

    Each line that the script writes is logged on its own, after the script's name: a line of its
    standard output at INFO, its report, and a line of its standard error at WARNING, since a
    script writes problems there. The start, and the time that it took, are logged at INFO.

    .. code-block:: text

        smarter.apps.account.repository_scripts.run_script() scripts/create-course-database.sh: checked: smarter_test_db.courses has 48 courses

    :param local_path: The repository's clone.
    :param script: The script's configuration.
    :param env: The script's environment, from :func:`script_environment`.
    :returns: What the script wrote to its standard output.
    :rtype: str
    :raises SmarterValueError: If the script exits non-zero, or runs out of time.
    """
    path = os.path.join(SCRIPTS_FOLDER, script.path)
    command = [os.path.join(local_path, path), *script.args]
    logger.info(
        "%s.run_script() %s: running, as a %s script, with a timeout of %ss.",
        logger_prefix,
        path,
        script.stage,
        script.timeout,
    )
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=local_path, env=env, capture_output=True, text=True, timeout=script.timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise SmarterValueError(f"did not finish in {script.timeout} seconds.") from e
    except OSError as e:
        raise SmarterValueError(f"could not run: {e}") from e
    for line in result.stdout.splitlines():
        if line.strip():
            logger.info("%s.run_script() %s: %s", logger_prefix, path, line)
    for line in result.stderr.splitlines():
        if line.strip():
            logger.warning("%s.run_script() %s: %s", logger_prefix, path, line)
    if result.returncode != 0:
        raise SmarterValueError(f"failed with exit code {result.returncode}: {result.stderr.strip()}")
    logger.info("%s.run_script() %s: finished in %.1fs.", logger_prefix, path, time.monotonic() - started)
    return result.stdout.strip()
