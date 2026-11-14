"""Test :mod:`smarter.apps.account.repository_owners`, the owners of a repository's folders."""

import os
import shutil
import tempfile

from pydantic import ValidationError

from smarter.apps.account.repository_owners import (
    OWNERS_CONFIG,
    RepositoryOwner,
    RepositoryOwnersConfig,
    load_owners_config,
    owners_config_path,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase


def owner(path: str, username: str = "it_admin", account_number: str = "1234-5678-0001") -> dict:
    """One entry of owners.yaml."""
    return {"path": path, "username": username, "accountNumber": account_number}


class TestRepositoryOwners(SmarterTestBase):
    """Test the owners file's model, the folder a file belongs to, and reading the file."""

    def repo(self, owners_yaml: str | None) -> str:
        """A local repository folder, with owners.yaml if it is given."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        if owners_yaml is not None:
            with open(os.path.join(root, OWNERS_CONFIG), "w", encoding="utf-8") as f:
                f.write(owners_yaml)
        return root

    def test_path_stays_in_the_repository(self):
        """A folder is normalized, and must be inside the repository, and not its root."""
        self.assertEqual(RepositoryOwner(**owner("departments/hr/")).path, os.path.normpath("departments/hr"))
        for path in ("", "/etc", "..", "../elsewhere", "."):
            with self.subTest(path=path), self.assertRaises(ValidationError):
                RepositoryOwner(**owner(path))

    def test_account_number_is_checked(self):
        """The account must be an account number."""
        with self.assertRaises(ValidationError):
            RepositoryOwner(**owner("departments/hr", account_number="not-an-account"))

    def test_folders_are_unique(self):
        """A folder may be listed only once."""
        with self.assertRaisesRegex(ValidationError, "only once"):
            RepositoryOwnersConfig.model_validate({"owners": [owner("a"), owner("a", username="other")]})

    def test_owner_for_the_deepest_folder(self):
        """A file belongs to the deepest listed folder that contains it, and to none outside them."""
        config = RepositoryOwnersConfig.model_validate(
            {"owners": [owner("departments", username="company"), owner("departments/hr", username="hr")]}
        )
        hr = config.owner_for("departments/hr/plugins/hr.yaml")
        company = config.owner_for("departments/accounting/a.yaml")
        assert hr is not None and company is not None
        self.assertEqual(hr.username, "hr")
        self.assertEqual(company.username, "company")
        self.assertIsNone(config.owner_for("secrets/s.yaml"))
        # a folder whose name only starts with a listed one isn't inside it.
        self.assertIsNone(config.owner_for("departments-old/x.yaml"))

    def test_load_owners_config(self):
        """The file is read and validated, and a repository may have none."""
        root = self.repo(
            'owners:\n  - path: departments/it\n    username: it_admin\n    accountNumber: "1234-5678-0001"\n'
        )
        config = load_owners_config(root)
        assert config is not None
        self.assertEqual(config.owners[0].username, "it_admin")
        self.assertEqual(owners_config_path(root), os.path.join(root, OWNERS_CONFIG))
        self.assertIsNone(load_owners_config(self.repo(None)))
        empty = load_owners_config(self.repo(""))
        assert empty is not None
        self.assertEqual(empty.owners, [])

    def test_load_owners_config_failures(self):
        """A file that isn't YAML, or isn't a valid configuration, fails."""
        for text in ("owners: [unclosed", "owners:\n  - path: x\n", "unknown: 1\n"):
            with self.subTest(text=text), self.assertRaises(SmarterValueError):
                load_owners_config(self.repo(text))
