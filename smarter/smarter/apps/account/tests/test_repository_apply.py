"""
Test the Apply page's batch apply of a GitHub repository, :mod:`smarter.apps.account.repository_apply`,.

its Celery task, and its web api, :mod:`smarter.apps.account.api.web.repository_apply`.

The repository is a local temporary folder, which the patched ``clone_repo()`` copies, as the
load_from_github command's tests do, so nothing is fetched from GitHub. The manifests are really
applied, as the test account's user, through the same brokers as the command.
"""

import os
import shutil
import subprocess
import tempfile
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from smarter.apps.account import repository_apply
from smarter.apps.account.api.web.urls import AccountApiWebReverseNames
from smarter.apps.account.models import (
    RepositoryApply,
    RepositoryApplyManifest,
    RepositoryApplyManifestStatus,
    RepositoryApplyStatus,
)
from smarter.apps.account.repository_apply import (
    REPOSITORY_APPLIES_PER_DAY,
    RepositoryApplyRefused,
    RepositoryApplyResponse,
    RepositoryLoader,
    normalize_repository_url,
    recent_runs,
    run_repository_apply,
    start_repository_apply,
    tail,
)
from smarter.apps.account.repository_owners import OWNERS_CONFIG
from smarter.apps.account.tasks import apply_repository
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.annotation.const import (
    SOURCE_COMMIT_ANNOTATION,
    SOURCE_REPOSITORY_ANNOTATION,
)

URL = "https://github.com/smarter-sh/no-such-repo"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
CLONE = "clone-folder"
"""Where a test's patched git would clone to: nothing is written there."""


def manifest(kind: str, name: str, spec: str) -> str:
    """A minimal manifest of ``kind``, named ``name``, as the load_from_github tests write them."""
    return f"apiVersion: smarter.sh/v1\nkind: {kind}\nmetadata:\n  name: {name}\n  description: a test\n  version: 1.0.0\nspec:\n{spec}"


class TestRepositoryApply(TestAccountMixin):
    """A batch apply finds, applies and records each manifest of a repository, as the user who started it."""

    def setUp(self):
        super().setUp()
        self.secret_name = f"test_repository_apply_{self.hash_suffix}".lower()
        self.bad_name = f"{self.secret_name}_bad"
        self.owned_name = f"{self.secret_name}_owned"
        for name in (self.secret_name, self.bad_name, self.owned_name):
            self.addCleanup(Secret.objects.filter(name=name).delete)
        self.addCleanup(RepositoryApply.objects.filter(user_profile__account=self.account).delete)

    def repo(self, files: dict[str, str]) -> str:
        """A local repository folder, with each file's content by its path."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for path, content in files.items():
            filespec = os.path.join(root, path)
            os.makedirs(os.path.dirname(filespec), exist_ok=True)
            with open(filespec, "w", encoding="utf-8") as f:
                f.write(content)
        return root

    def use_repo(self, root: str) -> None:
        """Make the loader copy ``root`` in place of cloning the repository."""
        patches = (
            patch.object(RepositoryLoader, "head_commit", return_value=COMMIT),
            patch.object(
                RepositoryLoader,
                "clone_repo",
                side_effect=lambda local_path: shutil.copytree(root, local_path, dirs_exist_ok=True),
            ),
        )
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def mixed_repo(self) -> str:
        """A repository with a manifest that applies, one that fails, one that owners.yaml owns, and a README."""
        secret_spec = "  config:\n    value: x\n"
        owners = f'owners:\n  - path: departments/hr\n    username: someone\n    accountNumber: "{self.account.account_number}"\n'
        return self.repo(
            {
                "secrets/good.yaml": manifest("Secret", self.secret_name, secret_spec),
                "secrets/bad.yaml": manifest("Secret", self.bad_name, "  config:\n    no_such_field: x\n"),
                "departments/hr/secret.yaml": manifest("Secret", self.owned_name, secret_spec),
                OWNERS_CONFIG: owners,
                "README.md": "# not a manifest\n",
            }
        )

    def new_run(self, **fields) -> RepositoryApply:
        return RepositoryApply.objects.create(user_profile=self.user_profile, url=URL, **fields)

    # the url
    # ---------------------------------------------------------------------------------------------

    def test_normalize_repository_url(self):
        accepted = {
            "https://github.com/smarter-sh/example-manifests": "https://github.com/smarter-sh/example-manifests",
            " https://github.com/smarter-sh/stackademy.git ": "https://github.com/smarter-sh/stackademy",
            "https://github.com/a-b/c_d.e/": "https://github.com/a-b/c_d.e",
        }
        for url, expected in accepted.items():
            with self.subTest(url=url):
                self.assertEqual(normalize_repository_url(url), expected)
        refused = [
            "",
            "http://github.com/a/b",
            "https://gitlab.com/a/b",
            "https://github.com/a",
            "https://github.com/a/b/tree/main",
            "https://github.com/-a/b",
            "https://github.com/a/-b",
            "https://github.com/a/..",
            "--upload-pack=touch /tmp/x",
            "https://user:pass@github.com/a/b",
            "file:///etc",
        ]
        for url in refused:
            with self.subTest(url=url):
                with self.assertRaises(RepositoryApplyRefused):
                    normalize_repository_url(url)

    def test_tail(self):
        self.assertEqual(tail("abc", 5), "abc")
        self.assertEqual(tail("abcdef", 3), "…def")

    # cloning
    # ---------------------------------------------------------------------------------------------

    def test_clone_repo_never_prompts(self):
        loader = RepositoryLoader(URL, self.user_profile)
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(repository_apply.subprocess, "run", return_value=result) as run:
            loader.clone_repo(CLONE)
        command = run.call_args.args[0]
        self.assertEqual(command[-3:], ["--", URL, CLONE])
        self.assertIn("--depth", command)
        env = run.call_args.kwargs["env"]
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(run.call_args.kwargs["timeout"], repository_apply.CLONE_TIMEOUT_SECONDS)

    def test_clone_repo_failures(self):
        loader = RepositoryLoader(URL, self.user_profile)
        failed = subprocess.CompletedProcess(args=[], returncode=128, stdout="", stderr="Repository not found.")
        with patch.object(repository_apply.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(SmarterValueError, "public"):
                loader.clone_repo(CLONE)
        timeout = subprocess.TimeoutExpired(cmd="git", timeout=1)
        with patch.object(repository_apply.subprocess, "run", side_effect=timeout):
            with self.assertRaisesRegex(SmarterValueError, "longer than"):
                loader.clone_repo(CLONE)

    # running
    # ---------------------------------------------------------------------------------------------

    def test_run_applies_skips_and_fails(self):
        """Each manifest's result is recorded: applied, skipped (owners.yaml) or failed, with why."""
        self.use_repo(self.mixed_repo())
        run = run_repository_apply(self.new_run().pk)
        self.assertEqual(run.status, RepositoryApplyStatus.FINISHED)
        self.assertEqual(run.commit, COMMIT)
        self.assertIsNotNone(run.completed_at)
        rows = {row.path: row for row in RepositoryApplyManifest.objects.filter(repository_apply=run)}
        self.assertEqual(set(rows), {"secrets/good.yaml", "secrets/bad.yaml", "departments/hr/secret.yaml"})

        good = rows["secrets/good.yaml"]
        self.assertEqual(good.status, RepositoryApplyManifestStatus.APPLIED)
        self.assertEqual(good.message, "")
        secret = Secret.objects.get(name=self.secret_name, user_profile=self.user_profile)
        self.assertEqual(secret.annotations[SOURCE_REPOSITORY_ANNOTATION], URL)
        self.assertEqual(secret.annotations[SOURCE_COMMIT_ANNOTATION], COMMIT)

        bad = rows["secrets/bad.yaml"]
        self.assertEqual(bad.status, RepositoryApplyManifestStatus.FAILED)
        self.assertFalse(bad.message.startswith("secrets/bad.yaml"))
        self.assertFalse(bad.message.startswith("bad.yaml"))
        self.assertFalse(Secret.objects.filter(name=self.bad_name).exists())

        owned = rows["departments/hr/secret.yaml"]
        self.assertEqual(owned.status, RepositoryApplyManifestStatus.SKIPPED)
        self.assertIn("owners.yaml", owned.message)
        self.assertFalse(Secret.objects.filter(name=self.owned_name).exists())

        response = RepositoryApplyResponse.from_model(run)
        self.assertEqual(response.counts, {"pending": 0, "applied": 1, "skipped": 1, "failed": 1})
        source_urls = [m.source_url for m in response.manifests]
        self.assertIn(f"{URL}/blob/{COMMIT}/secrets/good.yaml", source_urls)

    def test_run_skips_what_the_command_skips(self):
        """A manifest that load_from_github skips, e.g. of a disabled kind, is skipped, with the command's reason."""
        self.use_repo(self.repo({"secrets/s.yaml": manifest("Secret", self.secret_name, "  config:\n    value: x\n")}))
        with patch.object(RepositoryLoader, "apply_manifest", return_value=[]):
            run = run_repository_apply(self.new_run().pk)
        row = RepositoryApplyManifest.objects.get(repository_apply=run)
        self.assertEqual(row.status, RepositoryApplyManifestStatus.SKIPPED)

    def test_run_survives_an_exception(self):
        self.use_repo(self.repo({"secrets/s.yaml": manifest("Secret", self.secret_name, "  config:\n    value: x\n")}))
        with patch.object(RepositoryLoader, "apply_manifest", side_effect=RuntimeError("boom")):
            run = run_repository_apply(self.new_run().pk)
        self.assertEqual(run.status, RepositoryApplyStatus.FINISHED)
        row = RepositoryApplyManifest.objects.get(repository_apply=run)
        self.assertEqual(row.status, RepositoryApplyManifestStatus.FAILED)
        self.assertIn("RuntimeError: boom", row.message)

    def test_run_failures_as_a_whole(self):
        """A repository without manifests, with too many, or that can't be cloned, fails the run."""
        cases = {
            "no Smarter manifest": ({"README.md": "# hi\n"}, None),
            "at most 1": (
                {
                    "secrets/a.yaml": manifest("Secret", self.secret_name, "  config:\n    value: x\n"),
                    "secrets/b.yaml": manifest("Secret", self.bad_name, "  config:\n    value: x\n"),
                },
                1,
            ),
        }
        for message, (files, limit) in cases.items():
            with self.subTest(message=message):
                self.use_repo(self.repo(files))
                with patch.object(repository_apply, "MAX_MANIFESTS", limit or repository_apply.MAX_MANIFESTS):
                    run = run_repository_apply(self.new_run().pk)
                self.assertEqual(run.status, RepositoryApplyStatus.FAILED)
                self.assertIn(message, run.error)
        failed_clone = SmarterValueError("The repository could not be cloned.")
        with patch.object(RepositoryLoader, "clone_repo", side_effect=failed_clone):
            run = run_repository_apply(self.new_run().pk)
        self.assertEqual(run.status, RepositoryApplyStatus.FAILED)
        self.assertEqual(run.error, "The repository could not be cloned.")
        self.assertFalse(Secret.objects.filter(name=self.secret_name).exists())

    def test_a_finished_run_is_not_run_again(self):
        run = self.new_run(status=RepositoryApplyStatus.FINISHED)
        with patch.object(RepositoryLoader, "clone_repo") as clone:
            run_repository_apply(run.pk)
        clone.assert_not_called()

    def test_task(self):
        self.use_repo(self.repo({"secrets/s.yaml": manifest("Secret", self.secret_name, "  config:\n    value: x\n")}))
        self.assertEqual(apply_repository(self.new_run().pk), "finished")

    # starting
    # ---------------------------------------------------------------------------------------------

    def test_start_queues_the_task(self):
        with patch("smarter.apps.account.tasks.apply_repository.delay") as delay:
            run, started = start_repository_apply(self.user_profile, f"{URL}.git")
        self.assertTrue(started)
        self.assertEqual(run.url, URL)
        delay.assert_called_once_with(run.pk)
        with patch("smarter.apps.account.tasks.apply_repository.delay") as delay:
            again, started = start_repository_apply(self.user_profile, URL)
        self.assertFalse(started)
        self.assertEqual(again.pk, run.pk)
        delay.assert_not_called()

    def test_start_refuses(self):
        with self.assertRaises(RepositoryApplyRefused):
            start_repository_apply(self.user_profile, "https://example.com/a/b")
        for _ in range(REPOSITORY_APPLIES_PER_DAY):
            self.new_run(status=RepositoryApplyStatus.FINISHED)
        with self.assertRaisesRegex(RepositoryApplyRefused, "a day"):
            start_repository_apply(self.user_profile, URL)

    def test_a_stale_run_is_reported_failed(self):
        run = self.new_run(status=RepositoryApplyStatus.APPLYING)
        RepositoryApply.objects.filter(pk=run.pk).update(created_at=timezone.now() - timedelta(hours=1))
        run.refresh_from_db()
        self.assertTrue(run.is_stale)
        self.assertFalse(run.is_in_progress)
        response = RepositoryApplyResponse.from_model(run)
        self.assertEqual(response.status, "failed")
        self.assertIn("stopped", response.error)

    def test_recent_runs(self):
        self.new_run(status=RepositoryApplyStatus.FINISHED)
        runs = recent_runs(self.user_profile)
        self.assertEqual(len(runs.runs), 1)
        self.assertEqual(runs.runs[0].manifests, [])
        self.assertEqual(runs.runs_per_day, REPOSITORY_APPLIES_PER_DAY)


class TestRepositoryApplyWebApi(TestAccountMixin):
    """The Apply page starts a batch apply, lists the user's runs, and polls one."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.non_admin_user)
        self.addCleanup(RepositoryApply.objects.filter(user_profile__account=self.account).delete)
        namespace = AccountApiWebReverseNames.namespace
        self.list_url = reverse(f"{namespace}:{AccountApiWebReverseNames.repository_apply}")

    def detail_url(self, run_id: int) -> str:
        namespace = AccountApiWebReverseNames.namespace
        return reverse(f"{namespace}:{AccountApiWebReverseNames.repository_apply_detail}", kwargs={"run_id": run_id})

    def post(self, url: str):
        body = json.dumps({"url": url})
        with patch("smarter.apps.account.tasks.apply_repository.delay"):
            response = self.client.post(self.list_url, data=body, content_type="application/json")
        return response

    def test_start_poll_and_list(self):
        response = self.post(URL)
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED, response.content[:300])
        started = json.loads(response.content)
        self.assertEqual(started["url"], URL)
        self.assertEqual(started["status"], "queued")
        self.assertIn("createdAt", started)
        self.assertEqual(self.post(URL).status_code, HTTPStatus.OK)

        detail = self.client.get(self.detail_url(started["id"]))
        self.assertEqual(detail.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(detail.content)["id"], started["id"])

        listed = json.loads(self.client.get(self.list_url).content)
        self.assertEqual(listed["runs"][0]["id"], started["id"])
        self.assertIn("runsPerDay", listed)

    def test_bad_url(self):
        for body in ({"url": "https://example.com/a/b"}, {"url": 3}, {}):
            with self.subTest(body=body):
                response = self.client.post(self.list_url, data=json.dumps(body), content_type="application/json")
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                self.assertIn("error", json.loads(response.content))
        response = self.client.post(self.list_url, data=b"not json", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_another_users_run_is_not_found(self):
        run = RepositoryApply.objects.create(user_profile=self.user_profile, url=URL)
        response = self.client.get(self.detail_url(run.pk))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_requires_a_user(self):
        anonymous = Client()
        response = anonymous.get(self.list_url)
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
