"""Test the scripts of a repository that load_from_github loads, :mod:`smarter.apps.account.repository_scripts`."""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from pydantic import SecretStr, ValidationError

from smarter.apps.account.repository_scripts import (
    SCRIPT_DEFAULT_TIMEOUT,
    SCRIPT_MAX_TIMEOUT,
    SCRIPT_STAGE_POST,
    SCRIPT_STAGE_PRE,
    SCRIPTS_CONFIG,
    SCRIPTS_FOLDER,
    RepositoryScript,
    RepositoryScriptsConfig,
    load_scripts_config,
    run_script,
    script_environment,
    scripts_config_path,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.account.repository_scripts"


class TestRepositoryScripts(SmarterTestBase):
    """Test the scripts configuration, the scripts' environment, and running a script."""

    def repo(self, config: str | None = None, scripts: dict[str, str] | None = None, executable: bool = True) -> str:
        """
        A local repository with a scripts folder.

        :param config: The content of scripts/scripts.yaml, or None for no configuration file.
        :param scripts: Each script's content, by its file name in the scripts folder.
        :param executable: Whether the scripts are executable.
        :returns: The repository's folder.
        """
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        os.makedirs(os.path.join(root, SCRIPTS_FOLDER))
        if config is not None:
            with open(scripts_config_path(root), "w", encoding="utf-8") as f:
                f.write(config)
        for name, content in (scripts or {}).items():
            filespec = os.path.join(root, SCRIPTS_FOLDER, name)
            with open(filespec, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(filespec, 0o755 if executable else 0o644)  # nosec B103
        return root

    # -------------------------------------------------------------------------
    # the configuration
    # -------------------------------------------------------------------------
    def test_script_defaults(self):
        script = RepositoryScript(path="./a.sh", stage="pre")
        self.assertEqual(script.path, "a.sh")
        self.assertEqual((script.args, script.timeout, script.description), ([], SCRIPT_DEFAULT_TIMEOUT, None))

    def test_script_path_stays_in_the_scripts_folder(self):
        """A path must be relative, and inside the scripts folder."""
        self.assertEqual(RepositoryScript(path="sub/../b.sh", stage="post").path, "b.sh")
        for path in ("", "  ", "/etc/passwd", "..", "../x.sh", "sub/../../x.sh"):
            with self.subTest(path=path):
                with self.assertRaises(ValidationError):
                    RepositoryScript(path=path, stage="pre")

    def test_script_fields_are_checked(self):
        """The stage is pre or post, the timeout is bounded, and unknown fields are rejected."""
        for fields in (
            {"stage": "sometime"},
            {"stage": "pre", "timeout": 0},
            {"stage": "pre", "timeout": SCRIPT_MAX_TIMEOUT + 1},
            {"stage": "pre", "when": "now"},
        ):
            with self.subTest(fields=fields):
                with self.assertRaises(ValidationError):
                    RepositoryScript(path="a.sh", **fields)

    def test_for_stage_keeps_the_order(self):
        config = RepositoryScriptsConfig(
            scripts=[
                RepositoryScript(path="1.sh", stage="post"),
                RepositoryScript(path="2.sh", stage="pre"),
                RepositoryScript(path="3.sh", stage="post"),
            ]
        )
        self.assertEqual([s.path for s in config.for_stage(SCRIPT_STAGE_PRE)], ["2.sh"])
        self.assertEqual([s.path for s in config.for_stage(SCRIPT_STAGE_POST)], ["1.sh", "3.sh"])

    def test_load_scripts_config(self):
        root = self.repo(
            "scripts:\n  - path: a.sh\n    stage: pre\n    args: [x]\n    timeout: 60\n",
            {"a.sh": "#!/bin/sh\n", "data.sql": "SELECT 1;\n"},
        )
        config = load_scripts_config(root)
        self.assertIsNotNone(config)
        self.assertEqual(config.scripts, [RepositoryScript(path="a.sh", stage="pre", args=["x"], timeout=60)])

    def test_load_scripts_config_without_a_configuration(self):
        """No configuration file is no configuration, and an empty one has no scripts."""
        self.assertIsNone(load_scripts_config(self.repo()))
        self.assertEqual(load_scripts_config(self.repo("")).scripts, [])

    def test_load_scripts_config_failures(self):
        """Invalid YAML, an invalid configuration, a missing script and a script that isn't executable are errors."""
        relative = f"{SCRIPTS_FOLDER}/{SCRIPTS_CONFIG}"
        for root, message in (
            (self.repo("scripts: [\n"), f"{relative} is not valid"),
            (self.repo("scripts:\n  - {path: a.sh}\n"), f"{relative} is not valid"),
            (self.repo("scripts:\n  - {path: a.sh, stage: pre}\n"), "names a.sh, which is not in scripts/"),
            (
                self.repo("scripts:\n  - {path: a.sh, stage: pre}\n", {"a.sh": "#!/bin/sh\n"}, executable=False),
                "names a.sh, which is not executable",
            ),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(SmarterValueError, message):
                    load_scripts_config(root)

    # -------------------------------------------------------------------------
    # the environment
    # -------------------------------------------------------------------------
    def environment(self, password: str | None) -> dict[str, str]:
        with (
            patch(f"{MODULE}.smarter_settings") as settings,
            patch.dict(os.environ, {"PATH": "/usr/bin", "SMARTER_OPENAI_API_KEY": "sk-not-for-scripts"}),
        ):
            settings.mysql_root_username = "root"
            settings.mysql_root_password = SecretStr(password) if password else None
            return script_environment(
                url="https://github.com/a/b", local_path="/repo", account_number="1234-5678-9012", username="admin"
            )

    def test_script_environment(self):
        """A script receives the documented variables, and none of the platform's own credentials."""
        env = self.environment("root-pw")
        self.assertEqual(env["SMARTER_REPOSITORY_URL"], "https://github.com/a/b")
        self.assertEqual(env["SMARTER_REPOSITORY_ROOT"], "/repo")
        self.assertEqual(env["SMARTER_ACCOUNT_NUMBER"], "1234-5678-9012")
        self.assertEqual(env["SMARTER_USERNAME"], "admin")
        self.assertEqual(env["SMARTER_DATABASE_ADMIN_USERNAME"], "root")
        self.assertTrue(env["SMARTER_DATABASE_HOST"])
        self.assertTrue(env["SMARTER_DATABASE_PORT"].isdigit())
        self.assertEqual(env["MYSQL_PWD"], "root-pw")
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertNotIn("SMARTER_OPENAI_API_KEY", env)
        self.assertNotIn("sk-not-for-scripts", env.values())

    def test_script_environment_without_a_password(self):
        self.assertNotIn("MYSQL_PWD", self.environment(None))

    # -------------------------------------------------------------------------
    # running
    # -------------------------------------------------------------------------
    def test_run_script(self):
        """A script runs in the repository's root folder, with its arguments and environment."""
        root = self.repo(scripts={"a.sh": '#!/bin/sh\necho "$(pwd) $1 $GREETING"\n'})
        output = run_script(root, RepositoryScript(path="a.sh", stage="pre", args=["arg"]), {"GREETING": "hello"})
        self.assertEqual(output, f"{os.path.realpath(root)} arg hello")

    def test_run_script_logs_each_line(self):
        """Each line of standard output is logged at INFO, each line of standard error at WARNING, after the script's name."""
        root = self.repo(scripts={"a.sh": "#!/bin/sh\necho one\necho\necho two\necho careful >&2\n"})
        with patch(f"{MODULE}.logger") as logger:
            run_script(root, RepositoryScript(path="a.sh", stage="post"), {})
        info = [call.args for call in logger.info.call_args_list]
        self.assertIn(f"{SCRIPTS_FOLDER}/a.sh", info[0])
        self.assertIn("post", info[0])
        self.assertEqual(
            [args[2:] for args in info[1:3]], [(f"{SCRIPTS_FOLDER}/a.sh", "one"), (f"{SCRIPTS_FOLDER}/a.sh", "two")]
        )
        self.assertIn("finished in", info[-1][0])
        self.assertEqual(len(info), 4)  # the empty line is not logged
        logger.warning.assert_called_once()
        self.assertEqual(logger.warning.call_args.args[2:], (f"{SCRIPTS_FOLDER}/a.sh", "careful"))

    def test_run_script_failures(self):
        """A non-zero exit, a timeout, and a script that can't start are errors."""
        root = self.repo(scripts={"bad.sh": "#!/bin/sh\necho broken >&2\nexit 2\n"})
        with self.assertRaisesRegex(SmarterValueError, "failed with exit code 2: broken"):
            run_script(root, RepositoryScript(path="bad.sh", stage="pre"), {})
        script = RepositoryScript(path="bad.sh", stage="pre", timeout=5)
        with patch(f"{MODULE}.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="bad.sh", timeout=5)):
            with self.assertRaisesRegex(SmarterValueError, "did not finish in 5 seconds"):
                run_script(root, script, {})
        with self.assertRaisesRegex(SmarterValueError, "could not run"):
            run_script(root, RepositoryScript(path="missing.sh", stage="pre"), {})
