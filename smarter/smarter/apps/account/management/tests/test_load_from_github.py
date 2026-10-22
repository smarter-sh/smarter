"""
Test the load_from_github management command, :mod:`smarter.apps.account.management.commands.load_from_github`.

The repository is a local temporary folder, which the patched ``clone_repo()`` copies, so nothing is fetched
from GitHub. A failure that the command reports with ``handle_completed_failure(msg=...)`` doesn't exit: it
raises a ``CommandError``, or, for a bad argument, a ``SmarterValueError``.
"""

import os
import shutil
import subprocess
import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.account.management.commands.load_from_github import (
    Command,
    RepositoryManifest,
)
from smarter.apps.account.repository_scripts import SCRIPTS_CONFIG, SCRIPTS_FOLDER
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.lib.manifest.template import manifest_template_values

MODULE = "smarter.apps.account.management.commands.load_from_github"
URL = "https://github.com/smarter-sh/no-such-repo"


def manifest(kind: str, name: str, spec: str = "  config: {}\n") -> str:
    """A minimal manifest of ``kind``, named ``name``."""
    return f"apiVersion: smarter.sh/v1\nkind: {kind}\nmetadata:\n  name: {name}\n  description: a test\n  version: 1.0.0\nspec:\n{spec}"


class TestLoadFromGithub(TestAccountMixin):
    """Test that load_from_github applies a repository's manifests, in the order of their dependencies."""

    def setUp(self):
        super().setUp()
        self.secret_name = f"test_load_from_github_{self.hash_suffix}".lower()
        self.addCleanup(Secret.objects.filter(name=self.secret_name).delete)

    def repo(self, files: dict[str, str]) -> str:
        """
        A local repository folder.

        :param files: Each file's content, by its path relative to the repository's root.
        :returns: The folder.
        """
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for path, content in files.items():
            filespec = os.path.join(root, path)
            os.makedirs(os.path.dirname(filespec), exist_ok=True)
            with open(filespec, "w", encoding="utf-8") as f:
                f.write(content)
        return root

    def use_repo(self, root: str) -> MagicMock:
        """Make the command copy ``root`` in place of cloning the repository."""
        patcher = patch.object(
            Command, "clone_repo", side_effect=lambda local_path: shutil.copytree(root, local_path, dirs_exist_ok=True)
        )
        self.addCleanup(patcher.stop)
        return patcher.start()

    def run_command(self, *args, **kwargs) -> str:
        out = StringIO()
        call_command(
            "load_from_github",
            *args,
            url=URL,
            username=self.admin_user.username,
            stdout=out,
            stderr=out,
            **kwargs,
        )
        return out.getvalue()

    # -------------------------------------------------------------------------
    # the order of the kinds: SAMKinds.apply_order(), tested in test_enum.py
    # -------------------------------------------------------------------------
    def test_unknown_kind_is_last(self):
        item = RepositoryManifest(path="a.yaml", filespec="/a.yaml", kind="NoSuchKind", name="a", manifest={})
        self.assertEqual(item.rank, len(SAMKinds.apply_order()))
        secret = RepositoryManifest(path="s.yaml", filespec="/s.yaml", kind="Secret", name="s", manifest={})
        self.assertEqual(secret.rank, SAMKinds.apply_rank(SAMKinds.SECRET))

    # -------------------------------------------------------------------------
    # finding the manifests
    # -------------------------------------------------------------------------
    def test_find_manifests(self):
        """Test that the manifests are found in dependency order, and everything else is ignored."""
        root = self.repo(
            {
                "llm-clients/b.yaml": manifest("LLMClient", "b"),
                "plugins/sql/p.yml": manifest("SqlPlugin", "p"),
                "connections/api/c.yaml.tpl": manifest(
                    "ApiConnection", "c", "  connection:\n    baseUrl: ${environment_platform_scheme}://x\n"
                ),
                "secrets/s.yaml": manifest("Secret", "s"),
                "budgets/z.yaml": manifest("Budget", "z"),
                "README.md": "# not a manifest\n",
                "not-smarter.yaml": "apiVersion: v1\nkind: ConfigMap\n",
                "empty.yaml": "",
                ".pre-commit-config.yaml": "repos: []\n",
                ".github/dependabot.yml": manifest("Secret", "hidden"),
            }
        )
        command = Command(stdout=StringIO())
        manifests = command.find_manifests(root)
        self.assertEqual(
            [m.path for m in manifests],
            [
                "secrets/s.yaml",
                "connections/api/c.yaml.tpl",
                "plugins/sql/p.yml",
                "llm-clients/b.yaml",
                "budgets/z.yaml",
            ],
        )
        connection = manifests[1]
        self.assertEqual((connection.kind, connection.name), ("ApiConnection", "c"))
        self.assertEqual(
            connection.manifest["spec"]["connection"]["baseUrl"],
            f"{manifest_template_values()['environment_platform_scheme']}://x",
        )
        output = command.stdout.getvalue()
        self.assertIn("Skipped not-smarter.yaml", output)
        self.assertIn("Skipped empty.yaml", output)
        self.assertNotIn("dependabot", output)

    # -------------------------------------------------------------------------
    # applying
    # -------------------------------------------------------------------------
    def test_applies_a_manifest(self):
        """Test that a manifest is really applied, as the user, and that applying it again updates it."""
        self.use_repo(self.repo({"secrets/s.yaml": manifest("Secret", self.secret_name, "  config:\n    value: x\n")}))
        output = self.run_command()
        self.assertIn(f"Applied Secret {self.secret_name}, from secrets/s.yaml.", output)
        self.assertIn("Applied the 1 manifests", output)
        self.assertTrue(Secret.objects.filter(name=self.secret_name, user_profile=self.user_profile).exists())
        self.run_command()
        self.assertEqual(Secret.objects.filter(name=self.secret_name).count(), 1)

    def test_applies_in_dependency_order(self):
        self.use_repo(
            self.repo(
                {
                    "a/plugin.yaml": manifest("SqlPlugin", "p"),
                    "b/connection.yaml": manifest("SqlConnection", "c"),
                    "c/secret.yaml": manifest("Secret", "s"),
                }
            )
        )
        with patch.object(Command, "apply", return_value=None) as apply:
            self.run_command()
        self.assertEqual(
            [os.path.basename(call.args[0]) for call in apply.call_args_list],
            ["secret.yaml", "connection.yaml", "plugin.yaml"],
        )

    def test_excluded_kind_is_skipped(self):
        self.use_repo(self.repo({"secrets/s.yaml": manifest("Secret", "s"), "budgets/b.yaml": manifest("Budget", "b")}))
        with patch.object(Command, "apply", return_value=None) as apply:
            output = self.run_command(exclude_kind=["Budget"])
        self.assertEqual([os.path.basename(call.args[0]) for call in apply.call_args_list], ["s.yaml"])
        self.assertIn("Skipped budgets/b.yaml: Budget is excluded.", output)

    def test_failures_are_reported_after_the_others_are_applied(self):
        self.use_repo(self.repo({"a.yaml": manifest("Secret", "a"), "b.yaml": manifest("Secret", "b")}))
        with patch.object(Command, "apply", side_effect=["a.yaml: ValueError: boom", None]) as apply:
            with self.assertRaisesRegex(CommandError, r"1 of the 2 manifests .* failed:\na.yaml: a.yaml: ValueError"):
                self.run_command()
        self.assertEqual(apply.call_count, 2)

    def test_a_repository_without_manifests_fails(self):
        self.use_repo(self.repo({"README.md": "# nothing here\n"}))
        with self.assertRaisesRegex(CommandError, "holds no Smarter manifest"):
            self.run_command()

    def test_llmclient_keeps_deployed_and_may_be_deployed(self):
        """Test that an LLMClient keeps its deployed value, and that --deploy deploys it."""
        self.use_repo(self.repo({"llm-clients/c.yaml": manifest("LLMClient", "c")}))
        kept = {"kind": "LLMClient", "metadata": {"name": "c"}, "spec": {"config": {"prompt": {"deployed": True}}}}
        with (
            patch(f"{MODULE}.AddExampleLLMClientsCommand.missing_extensions", return_value=[]),
            patch(f"{MODULE}.AddExampleLLMClientsCommand.keep_deployed", return_value=kept) as keep_deployed,
            patch(f"{MODULE}.DeployExampleLLMClientsCommand.deploy_manifest", return_value=True) as deploy_manifest,
            patch.object(Command, "apply", return_value=None) as apply,
        ):
            self.run_command()
            deploy_manifest.assert_not_called()
            self.run_command(deploy=True)
        self.assertEqual(keep_deployed.call_args.args[1], self.user_profile)
        self.assertIn('"deployed": true', apply.call_args.kwargs["manifest"])
        deploy_manifest.assert_called_once_with(kept)

    def test_llmclient_that_fails_to_deploy_is_a_failure(self):
        self.use_repo(self.repo({"llm-clients/c.yaml": manifest("LLMClient", "c")}))
        with (
            patch(f"{MODULE}.AddExampleLLMClientsCommand.missing_extensions", return_value=[]),
            patch(f"{MODULE}.DeployExampleLLMClientsCommand.deploy_manifest", return_value=False),
            patch.object(Command, "apply", return_value=None),
        ):
            with self.assertRaisesRegex(CommandError, "LLMClient c failed to deploy"):
                self.run_command(deploy=True)

    def test_llmclient_that_needs_a_missing_extension_is_skipped(self):
        self.use_repo(self.repo({"llm-clients/c.yaml": manifest("LLMClient", "c")}))
        with (
            patch(f"{MODULE}.AddExampleLLMClientsCommand.missing_extensions", return_value=["weather"]),
            patch.object(Command, "apply", return_value=None) as apply,
        ):
            output = self.run_command()
        apply.assert_not_called()
        self.assertIn("needs extensions that are not installed: weather", output)

    # -------------------------------------------------------------------------
    # the scripts. The scheme itself is tested in test_repository_scripts.py.
    # -------------------------------------------------------------------------
    def scripts_repo(self, config: str, scripts: dict[str, str]) -> str:
        """
        A local repository with one Secret manifest, and a scripts folder whose scripts are executable.

        :param config: The content of scripts/scripts.yaml.
        :param scripts: Each script's content, by its file name in the scripts folder.
        :returns: The folder.
        """
        root = self.repo({f"{SCRIPTS_FOLDER}/{SCRIPTS_CONFIG}": config, "secrets/s.yaml": manifest("Secret", "s")})
        for name, content in scripts.items():
            filespec = os.path.join(root, SCRIPTS_FOLDER, name)
            with open(filespec, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(filespec, 0o755)  # nosec B103
        return root

    def test_scripts_folder_holds_no_manifests(self):
        """Test that a manifest in the top-level scripts folder is not applied, but one in a nested scripts folder is."""
        root = self.repo(
            {
                f"{SCRIPTS_FOLDER}/s.yaml": manifest("Secret", "in_scripts"),
                "plugins/scripts/p.yaml": manifest("SqlPlugin", "nested"),
            }
        )
        self.assertEqual([m.path for m in Command(stdout=StringIO()).find_manifests(root)], ["plugins/scripts/p.yaml"])

    def test_scripts_run_before_and_after_the_manifests(self):
        """Test that --run_scripts runs the pre scripts, then applies the manifests, then runs the post scripts."""
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        log = os.path.join(folder, "log")
        self.use_repo(
            self.scripts_repo(
                "scripts:\n  - {path: after.sh, stage: post}\n  - {path: before.sh, stage: pre, args: [one]}\n",
                {
                    "before.sh": f'#!/bin/sh\necho "pre $1 $SMARTER_USERNAME" >> {log}\necho made it\n',
                    "after.sh": f"#!/bin/sh\necho post >> {log}\n",
                },
            )
        )

        def apply(*args, **kwargs):
            with open(log, "a", encoding="utf-8") as f:
                f.write("apply\n")

        with patch.object(Command, "apply", side_effect=apply):
            output = self.run_command(run_scripts=True)
        with open(log, encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines(), [f"pre one {self.admin_user.username}", "apply", "post"])
        self.assertNotIn("made it", output)  # run_script() logs it, rather than the command repeating it
        self.assertIn(f"Ran the pre script {SCRIPTS_FOLDER}/before.sh.", output)
        self.assertIn(f"Ran the post script {SCRIPTS_FOLDER}/after.sh.", output)

    def test_scripts_are_opt_in(self):
        """Test that without --run_scripts no script runs, and the command says so."""
        self.use_repo(self.scripts_repo("scripts:\n  - {path: x.sh, stage: pre}\n", {"x.sh": "#!/bin/sh\nexit 1\n"}))
        with patch(f"{MODULE}.run_script") as run_script, patch.object(Command, "apply", return_value=None):
            output = self.run_command()
        run_script.assert_not_called()
        self.assertIn(f"Skipped the scripts of {SCRIPTS_FOLDER}/{SCRIPTS_CONFIG}: --run_scripts is not set.", output)

    def test_a_failing_script_fails_the_command_after_the_rest(self):
        """Test that a failing script doesn't stop the manifests or the other scripts, and fails the command at the end."""
        self.use_repo(
            self.scripts_repo(
                "scripts:\n  - {path: bad.sh, stage: pre}\n  - {path: good.sh, stage: post}\n",
                {"bad.sh": "#!/bin/sh\necho broken >&2\nexit 3\n", "good.sh": "#!/bin/sh\necho fine\n"},
            )
        )
        out = StringIO()
        with patch.object(Command, "apply", return_value=None) as apply:
            with self.assertRaisesRegex(
                CommandError,
                f"1 of the scripts of {URL} failed:\n{SCRIPTS_FOLDER}/bad.sh: failed with exit code 3: broken",
            ):
                call_command(
                    "load_from_github", url=URL, username=self.admin_user.username, run_scripts=True, stdout=out
                )
        apply.assert_called_once()
        self.assertIn(f"Ran the post script {SCRIPTS_FOLDER}/good.sh.", out.getvalue())

    def test_an_invalid_scripts_config_fails_before_anything_runs(self):
        self.use_repo(self.scripts_repo("scripts:\n  - {path: x.sh, stage: sometime}\n", {"x.sh": "#!/bin/sh\n"}))
        with patch.object(Command, "apply", return_value=None) as apply:
            with self.assertRaisesRegex(CommandError, f"{SCRIPTS_FOLDER}/{SCRIPTS_CONFIG} is not valid"):
                self.run_command(run_scripts=True)
        apply.assert_not_called()

    # -------------------------------------------------------------------------
    # cloning
    # -------------------------------------------------------------------------
    def test_clone_repo(self):
        command = Command()
        command.url = URL
        with patch(f"{MODULE}.subprocess.call", return_value=0) as call:
            command.clone_repo("/a/folder")
        self.assertEqual(call.call_args.args[0], ["git", "clone", "--depth", "1", "--quiet", URL, "/a/folder"])
        with patch(f"{MODULE}.subprocess.call", return_value=128):
            with self.assertRaises(subprocess.CalledProcessError):
                command.clone_repo("/a/folder")

    def test_failed_clone_fails_and_removes_the_clone(self):
        folders = []

        def clone(local_path):
            folders.append(local_path)
            raise subprocess.CalledProcessError(returncode=128, cmd="git clone")

        with patch.object(Command, "clone_repo", side_effect=clone):
            with self.assertRaisesRegex(CommandError, f"Failed to load {URL}"):
                self.run_command()
        self.assertFalse(os.path.exists(folders[0]))

    # -------------------------------------------------------------------------
    # arguments
    # -------------------------------------------------------------------------
    def test_url_is_required(self):
        with self.assertRaises(SmarterValueError):
            _ = Command().url
        with self.assertRaises(SmarterValueError):
            call_command("load_from_github", username=self.admin_user.username, stdout=StringIO())

    def test_owner(self):
        """Test that the owner is the user, or else the account's admin, and that one of them is required."""
        command = Command()
        self.assertEqual(command.get_user_profile(None, self.admin_user.username), self.user_profile)
        self.assertEqual(command.get_user_profile(self.account.account_number, None).user, self.admin_user)
        for account_number, username in ((None, None), (None, "no_such_user_x"), ("9999-9999-9999", None)):
            with self.subTest(account_number=account_number, username=username):
                with self.assertRaises(SmarterValueError):
                    command.get_user_profile(account_number, username)
