"""
The owners of the folders of a repository that ``manage.py load_from_github`` loads.

``load_from_github`` applies a repository's manifests as one user, so that every resource belongs to one account.
An organization of several accounts (ADR-036) keeps its resources in the accounts of the departments that own them:
its IT department's Secrets and Connections in IT's account, its HR assistant in HR's, and so on. A repository says
which by mapping its folders to their owners. The Stackademy project, https://github.com/smarter-sh/stackademy, is the
reference.

The scheme
----------

- **The file.** ``owners.yaml``, :data:`OWNERS_CONFIG`, at the repository's root. Its model is
  :class:`RepositoryOwnersConfig`:

  .. code-block:: yaml

      owners:
        - path: departments/it                 # a folder, relative to the repository's root
          username: stackademy_it_admin        # the user who applies, and so owns, its manifests
          accountNumber: "2718-2818-0001"      # the account in which they own them

- **Which folder.** A manifest belongs to the deepest folder of the file that contains it, so a folder's owner may
  be overridden for one of its subfolders. A manifest in no listed folder is applied by ``load_from_github``'s own
  user, as before.
- **The organization itself.** Account and User manifests are always applied by ``load_from_github``'s own user,
  wherever they are, because they declare the accounts and the people that own the rest, and must exist first.
- **Where it applies.** Only when the repository is loaded into the Smarter account, as ``manage.py
  initialize_platform`` loads it: an organization's resources exist once. Loaded into any other account, e.g. by
  ``manage.py initialize_account``, which copies a repository's plugins and LLMClients into a new account, the
  manifests of owned folders are skipped, because they belong to their owners, not to that account.
- **Failures.** An owner who doesn't exist, or doesn't belong to the account that the file names, fails each of
  their manifests, and not the others. A file that is not valid fails ``load_from_github`` before anything is applied.
"""

import os
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator

logger = logging.getSmarterLogger(__name__)

OWNERS_CONFIG = "owners.yaml"
"""A repository's owners file, at its root, :class:`RepositoryOwnersConfig`."""


class RepositoryOwner(BaseModel):
    """One folder of ``owners.yaml``, and the user who applies, and so owns, its manifests."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(
        ...,
        description="The folder, relative to the repository's root, e.g. departments/it.",
        examples=["departments/it"],
    )
    username: str = Field(
        ..., description="The user who applies the folder's manifests.", examples=["stackademy_it_admin"]
    )
    accountNumber: str = Field(
        ...,
        description="The account in which the user owns them, which the user must belong to.",
        examples=["2718-2818-0001"],
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """
        Validate that the path is a folder inside the repository.

        :param v: The path.
        :returns: The path, normalized, without a trailing separator.
        :raises ValueError: If it is empty, absolute, the repository's root, or leaves the repository.
        """
        if not v or not v.strip():
            raise ValueError("path is required.")
        path = os.path.normpath(v.strip())
        if os.path.isabs(path) or path in (".", "..") or path.startswith(".." + os.sep):
            raise ValueError(f"path {v} must be a folder inside the repository.")
        return path

    @field_validator("accountNumber")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        """
        Validate that the account number has the form 1234-5678-9012.

        :param v: The account number.
        :returns: The account number.
        :raises ValueError: If it isn't an account number.
        """
        if not SmarterValidator.is_valid_account_number(v):
            raise ValueError(f"{v} is not an account number, e.g. 1234-5678-9012.")
        return v


class RepositoryOwnersConfig(BaseModel):
    """
    A repository's ``owners.yaml``: which user applies the manifests of each of its folders.

    See the scheme in :mod:`smarter.apps.account.repository_owners`.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    owners: list[RepositoryOwner] = Field(default_factory=list, description="The folders and their owners.")

    @field_validator("owners")
    @classmethod
    def validate_unique_paths(cls, v: list[RepositoryOwner]) -> list[RepositoryOwner]:
        """
        Validate that each folder is listed once.

        :param v: The owners.
        :returns: The owners.
        :raises ValueError: If a folder is listed more than once.
        """
        paths = [owner.path for owner in v]
        if len(paths) != len(set(paths)):
            raise ValueError("Each folder may be listed only once.")
        return v

    def owner_for(self, path: str) -> Optional[RepositoryOwner]:
        """
        Return the owner of the deepest listed folder that contains a file.

        :param path: The file, relative to the repository's root, e.g. ``departments/hr/plugins/hr.yaml``.
        :returns: Its folder's owner, or None if no listed folder contains it.
        :rtype: Optional[RepositoryOwner]
        """
        file_path = os.path.normpath(path)
        retval: Optional[RepositoryOwner] = None
        deepest = -1
        for owner in self.owners:
            folder = owner.path + os.sep
            if not file_path.startswith(folder):
                continue
            depth = owner.path.count(os.sep)
            if depth > deepest:
                deepest = depth
                retval = owner
        return retval


def owners_config_path(local_path: str) -> str:
    """
    Return the path of a repository's owners file, whether or not it exists.

    :param local_path: The repository's clone.
    :returns: ``<local_path>/owners.yaml``.
    :rtype: str
    """
    return os.path.join(local_path, OWNERS_CONFIG)


def load_owners_config(local_path: str) -> Optional[RepositoryOwnersConfig]:
    """
    Read and validate a repository's ``owners.yaml``.

    :param local_path: The repository's clone.
    :returns: The configuration, or None if the repository has none.
    :rtype: Optional[RepositoryOwnersConfig]
    :raises SmarterValueError: If the file is not valid YAML, or not a valid configuration.
    """
    filespec = owners_config_path(local_path)
    if not os.path.isfile(filespec):
        return None
    try:
        with open(filespec, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = RepositoryOwnersConfig.model_validate(data)
    except (yaml.YAMLError, ValidationError) as e:
        raise SmarterValueError(f"{OWNERS_CONFIG} is not valid: {e}") from e
    logger.debug("%s lists %s folders", OWNERS_CONFIG, len(config.owners))
    return config


__all__ = [
    "OWNERS_CONFIG",
    "RepositoryOwner",
    "RepositoryOwnersConfig",
    "load_owners_config",
    "owners_config_path",
]
