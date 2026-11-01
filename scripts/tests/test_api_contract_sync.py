"""
Tests of scripts/api_contract_sync.py, which the API Contract Sync workflow runs in each repository.

that copies the platform's api contract.

They need only the standard library, and never run git or gh: ``run`` is replaced by a fake that
records each command and answers it. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import importlib.util
import io
import json
import os
import subprocess  # nosec B404: only to build a CalledProcessError
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "api_contract_sync.py"
spec = importlib.util.spec_from_file_location("api_contract_sync", SCRIPT_PATH)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

RUN_URL = "https://github.com/smarter-sh/smarter/actions/runs/1"


def result(**overrides) -> "sync.Result":
    """A result of smarter-python, with the given fields."""
    values = {
        "repository": "smarter-sh/smarter-python",
        "tag": "v0.40.4",
        "sha": "a" * 40,
        "shipped": ["smarter/models/sam"],
    }
    values.update(overrides)
    return sync.Result(**values)


class FakeGitHub:
    """Stands in for run(): records every command, and answers gh's list and create commands."""

    def __init__(self, open_issue: dict | None = None, open_pr: dict | None = None):
        self.commands: list[tuple[str, ...]] = []
        self.inputs: list[str | None] = []
        self.open_issue = open_issue
        self.open_pr = open_pr

    def __call__(self, *args: str, check: bool = True, input_text: str | None = None) -> str:
        self.commands.append(args)
        self.inputs.append(input_text)
        if args[:3] == ("gh", "issue", "list"):
            return json.dumps([self.open_issue] if self.open_issue else [])
        if args[:3] == ("gh", "pr", "list"):
            return json.dumps([self.open_pr] if self.open_pr else [])
        if args[:3] == ("gh", "issue", "create"):
            return "https://github.com/smarter-sh/smarter-python/issues/7"
        if args[:3] == ("gh", "pr", "create"):
            return "https://github.com/smarter-sh/smarter-python/pull/8"
        return ""

    def ran(self, *prefix: str) -> list[tuple[str, ...]]:
        """The commands that start with prefix."""
        return [command for command in self.commands if command[: len(prefix)] == prefix]


class TestParsePorcelain(unittest.TestCase):
    """Git status --porcelain output becomes a sorted list of paths."""

    def test_paths(self):
        text = " M tests/data/contracts/openapi.json\n?? tests/data/sam/New.schema.json\nD  tests/data/sam/Old.example.json\n"
        self.assertEqual(
            sync.parse_porcelain(text),
            ["tests/data/contracts/openapi.json", "tests/data/sam/New.schema.json", "tests/data/sam/Old.example.json"],
        )

    def test_rename_and_quotes(self):
        self.assertEqual(
            sync.parse_porcelain('R  a.json -> b.json\n?? "with space.json"\n\nx\n'), ["b.json", "with space.json"]
        )

    def test_changed_files_reads_git_status(self):
        with mock.patch.object(sync, "run", return_value=" M sam/llmclient.go") as run:
            self.assertEqual(sync.changed_files(), ["sam/llmclient.go"])
        run.assert_called_once_with("git", "status", "--porcelain", "--untracked-files=all", strip=False)

    def test_run_keeps_the_leading_space_of_a_status(self):
        """A first line `` M path`` keeps its space, so its path is read whole."""
        completed = subprocess.CompletedProcess([], 0, stdout=" M testdata/contracts/openapi.json\n")
        with mock.patch.object(sync.subprocess, "run", return_value=completed):
            self.assertEqual(sync.changed_files(), ["testdata/contracts/openapi.json"])
            self.assertEqual(sync.run("gh", "pr", "create"), "M testdata/contracts/openapi.json")


class TestResult(unittest.TestCase):
    """A result's verdict, and its round trip through JSON."""

    def test_current(self):
        self.assertEqual(result().verdict, "current")
        self.assertFalse(result().out_of_sync)

    def test_a_source_record_alone_is_not_a_change(self):
        self.assertEqual(result(changed=["testdata/contracts/SOURCE"]).verdict, "current")
        self.assertTrue(result(changed=["testdata/contracts/SOURCE", "testdata/contracts/openapi.json"]).out_of_sync)

    def test_outdated(self):
        self.assertEqual(result(changed=["tests/data/contracts/openapi.json"]).verdict, "outdated")

    def test_broken(self):
        broken = result(changed=["tests/data/contracts/openapi.json"], tests="failure")
        self.assertTrue(broken.broken)
        self.assertEqual(broken.verdict, "broken")

    def test_failing_before_the_sync(self):
        self.assertEqual(result(baseline="failure", tests="failure").verdict, "failing")

    def test_ships_changes(self):
        self.assertTrue(result(changed=["smarter/models/sam/llmclient.py"]).ships_changes)
        self.assertFalse(result(changed=["smarter/models/samples.py", "tests/data/sam/x.json"]).ships_changes)
        self.assertTrue(result(shipped=["contract"], changed=["contract"]).ships_changes)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            original = result(changed=["a.json"], tests="failure", issue_url="https://example.com/1")
            original.save(path)
            self.assertEqual(sync.Result.load(path), original)


class TestText(unittest.TestCase):
    """The commit, issue and pull request text."""

    def test_commit_subject(self):
        self.assertEqual(
            sync.commit_subject(result(changed=["smarter/models/sam/x.py"])),
            "fix(contracts): sync with smarter v0.40.4",
        )
        self.assertEqual(
            sync.commit_subject(result(changed=["tests/data/sam/x.json"])),
            "chore(contracts): sync with smarter v0.40.4",
        )

    def test_commit_body_ends_with_the_platform_sha(self):
        body = sync.commit_body(result(), RUN_URL)
        self.assertTrue(body.endswith("Synced with smarter " + "a" * 40))
        self.assertIn(RUN_URL, body)

    def test_issue_body(self):
        compatible = sync.issue_body(result(changed=["a.json"]), RUN_URL)
        self.assertIn("compatible", compatible)
        self.assertIn("`a.json`", compatible)
        self.assertIn("make sam-models SMARTER_REF=v0.40.4", compatible)
        self.assertIn(
            "tests fail after the sync", sync.issue_body(result(changed=["a.json"], tests="failure"), RUN_URL)
        )
        self.assertIn("already fail", sync.issue_body(result(changed=["a.json"], baseline="failure"), RUN_URL))
        self.assertIn("v0.40.4", sync.issue_title(result()))

    def test_file_list_is_cut(self):
        text = sync.file_list([f"f{i}" for i in range(sync.MAX_FILES + 3)])
        self.assertIn("and 3 more", text)
        self.assertEqual(sync.file_list([]), "- (none)")

    def test_pull_request_body(self):
        body = sync.pull_request_body(result(changed=["a.json"], tests="failure"), RUN_URL, "7")
        self.assertIn("Closes #7", body)
        self.assertIn("Draft", body)
        self.assertNotIn("Closes", sync.pull_request_body(result(changed=["a.json"]), RUN_URL, ""))

    def test_outcome(self):
        self.assertEqual(sync.outcome("success"), "pass")
        self.assertEqual(sync.outcome("unknown"), "unknown")


class TestPublish(unittest.TestCase):
    """Publish opens, updates or closes the issue and pull request."""

    def publish(self, item: "sync.Result", fake: FakeGitHub, dry_run: bool = False, token: str = "ghp_test"):
        with (
            mock.patch.object(sync, "run", fake),
            mock.patch.dict(os.environ, {"GH_TOKEN": token}),
            redirect_stdout(io.StringIO()),
        ):
            return sync.publish(item, "alpha", RUN_URL, dry_run)

    def test_dry_run_writes_nothing(self):
        fake = FakeGitHub()
        self.publish(result(changed=["a.json"]), fake, dry_run=True)
        self.assertEqual(fake.commands, [])

    def test_no_token_writes_nothing(self):
        fake = FakeGitHub()
        self.publish(result(changed=["a.json"]), fake, token="")
        self.assertEqual(fake.commands, [])

    def test_failing_and_current_proposes_nothing(self):
        fake = FakeGitHub()
        self.publish(result(baseline="failure"), fake)
        self.assertEqual(fake.commands, [])

    def test_current_closes_the_earlier_issue_and_pull_request(self):
        fake = FakeGitHub(open_issue={"number": 3, "url": "u3"}, open_pr={"number": 4, "url": "u4"})
        self.publish(result(), fake)
        self.assertEqual(len(fake.ran("gh", "pr", "close", "4")), 1)
        self.assertEqual(len(fake.ran("gh", "issue", "close", "3")), 1)

    def test_current_with_nothing_open(self):
        fake = FakeGitHub()
        self.publish(result(), fake)
        self.assertEqual(fake.ran("gh", "pr", "close") + fake.ran("gh", "issue", "close"), [])

    def test_outdated_opens_an_issue_and_a_pull_request(self):
        fake = FakeGitHub()
        published = self.publish(result(changed=["smarter/models/sam/x.py"]), fake)
        self.assertEqual(published.issue_url, "https://github.com/smarter-sh/smarter-python/issues/7")
        self.assertEqual(published.pull_request_url, "https://github.com/smarter-sh/smarter-python/pull/8")
        self.assertEqual(len(fake.ran("gh", "label", "create", sync.LABEL)), 1)
        self.assertEqual(
            fake.ran("git", "push"), [("git", "push", "--force", "--quiet", "origin", f"HEAD:refs/heads/{sync.BRANCH}")]
        )
        commit = fake.inputs[fake.commands.index(fake.ran("git", "commit")[0])]
        self.assertTrue(commit.startswith("fix(contracts): sync with smarter v0.40.4\n\n"))
        create = fake.ran("gh", "pr", "create")[0]
        self.assertIn("alpha", create)
        self.assertNotIn("--draft", create)
        self.assertIn("Closes #7", fake.inputs[fake.commands.index(create)])

    def test_broken_opens_a_draft(self):
        fake = FakeGitHub()
        self.publish(result(changed=["a.json"], tests="failure"), fake)
        self.assertIn("--draft", fake.ran("gh", "pr", "create")[0])

    def test_a_later_run_updates_the_open_issue_and_pull_request(self):
        fake = FakeGitHub(open_issue={"number": 3, "url": "u3"}, open_pr={"number": 4, "url": "u4"})
        published = self.publish(result(changed=["a.json"], tests="failure"), fake)
        self.assertEqual((published.issue_url, published.pull_request_url), ("u3", "u4"))
        self.assertEqual(fake.ran("gh", "issue", "create") + fake.ran("gh", "pr", "create"), [])
        self.assertEqual(len(fake.ran("gh", "issue", "edit", "3")), 1)
        self.assertEqual(
            fake.ran("gh", "pr", "ready"), [("gh", "pr", "ready", "4", "--repo", "smarter-sh/smarter-python")]
        )

    def test_a_fixed_pull_request_leaves_draft(self):
        fake = FakeGitHub(open_issue={"number": 3, "url": "u3"}, open_pr={"number": 4, "url": "u4"})
        self.publish(result(changed=["a.json"]), fake)
        self.assertIn("--undo", fake.ran("gh", "pr", "ready")[0])


class TestReport(unittest.TestCase):
    """The job summary and the Slack message."""

    def test_clean_bill_of_health(self):
        message = sync.slack_message([result(), result(repository="smarter-sh/smarter-cli")], "v0.40.4", RUN_URL)
        self.assertIn("clean bill of health", message)
        self.assertIn("smarter-python, smarter-cli", message)

    def test_attention(self):
        results = [
            result(changed=["a.json"], issue_url="https://i", pull_request_url="https://p"),
            result(repository="smarter-sh/smarter-golang", changed=["a.json"], tests="failure"),
            result(repository="smarter-sh/smarter-cli"),
            result(repository="smarter-sh/smarter-nodejs", error="publishing failed: no"),
        ]
        message = sync.slack_message(results, "v0.40.4", RUN_URL)
        self.assertNotIn("clean bill of health", message)
        self.assertIn("smarter-python: out of date, compatible (<https://i|issue>, <https://p|pull request>)", message)
        self.assertIn("smarter-golang: out of date, tests fail after the sync", message)
        self.assertIn("publishing failed: no", message)
        self.assertIn("1 more current: smarter-cli", message)

    def test_no_results(self):
        self.assertIn("No repository reported", sync.slack_message([], "v0.40.4", RUN_URL))
        self.assertIn("(no results)", sync.summary_markdown([], "v0.40.4", RUN_URL))

    def test_summary(self):
        text = sync.summary_markdown([result(changed=["a.json"], issue_url="https://i", error="x")], "v0.40.4", RUN_URL)
        self.assertIn(
            "| smarter-sh/smarter-python | out of date, compatible (x) | pass | pass | 1 | [issue](https://i) |  |",
            text,
        )


class TestMain(unittest.TestCase):
    """The command line."""

    def run_main(self, *argv: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = sync.main(list(argv))
        return code, output.getvalue()

    def test_status(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(sync, "changed_files", return_value=["sam/x.go"]),
        ):
            path = Path(directory) / "r.json"
            code, _ = self.run_main(
                "status", "--repository", "smarter-sh/smarter-golang", "--tag", "v1", "--sha", "b",
                "--shipped", "sam", "--tests", "failure", "--output", str(path),
            )  # fmt: skip
            self.assertEqual(code, 0)
            saved = sync.Result.load(path)
        self.assertEqual((saved.changed, saved.shipped, saved.verdict), (["sam/x.go"], ["sam"], "broken"))

    def test_publish_records_a_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.json"
            result(changed=["a.json"]).save(path)
            error = subprocess.CalledProcessError(1, ["gh"], stderr="first\nHTTP 403: forbidden\n")
            with mock.patch.object(sync, "publish", side_effect=error), redirect_stdout(io.StringIO()):
                with mock.patch("sys.stderr", io.StringIO()):
                    code = sync.main(["publish", "--result", str(path)])
            self.assertEqual(code, 1)
            self.assertEqual(sync.Result.load(path).error, "publishing failed: HTTP 403: forbidden")

    def test_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.json"
            result().save(path)
            code, output = self.run_main("publish", "--result", str(path), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Dry run", output)

    def test_report(self):
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "results"
            results.mkdir()
            result().save(results / "python.json")
            (results / "broken.json").write_text("not json")
            summary = Path(directory) / "summary.md"
            code, output = self.run_main("report", "--results", str(results), "--tag", "v1", "--summary", str(summary))
            self.assertEqual(code, 0)
            self.assertIn("clean bill of health", output)
            self.assertIn("smarter-sh/smarter-python", summary.read_text())

            result(repository="smarter-sh/smarter-cli", changed=["a"], tests="failure").save(results / "cli.json")
            code, _ = self.run_main("report", "--results", str(results), "--tag", "v1")
            self.assertEqual(code, 1)

    def test_report_without_results_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            code, _ = self.run_main("report", "--results", directory, "--tag", "v1")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
