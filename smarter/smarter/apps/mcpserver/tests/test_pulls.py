"""Tests for smarter.apps.mcpserver.github.pulls.

GitHub is never contacted: requests.request is replaced by a fake GitHub, which answers each
request by its method and url.
"""

from typing import Optional
from unittest import mock

from pydantic import SecretStr

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github import pulls
from smarter.apps.mcpserver.github.pulls import (
    MAX_FILES,
    PULL_REQUEST_FOOTER,
    GitHubCommitAuthor,
    GitHubPullRequest,
    PullRequestFile,
    create_pull_request,
    validate_branch,
    validate_files,
)
from smarter.apps.mcpserver.repositories import ProjectRepository
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import TOKEN
from .test_github_client import REQUEST, response

API = "https://api.github.com/repos/smarter-sh/smarter-test"
BASE_SHA = "a" * 40
ROOT_TREE_SHA = "b" * 40
SCRIPTS_TREE_SHA = "c" * 40
NEW_TREE_SHA = "d" * 40
NEW_COMMIT_SHA = "e" * 40
PULL: SmarterDictType = {
    "number": 7,
    "title": "fix: the plugin timeout",
    "html_url": "https://github.com/smarter-sh/smarter-test/pull/7",
    "draft": True,
    "user": {"login": "octocat"},
}


def tree(sha: str, entries: list[tuple[str, str, str]]) -> SmarterDictType:
    """Return a git tree of (path, mode, type) entries."""
    return {
        "sha": sha,
        "tree": [{"path": path, "mode": mode, "type": kind, "sha": f"{path}-sha"} for path, mode, kind in entries],
    }


def fake_github(overrides: Optional[dict[tuple[str, str], mock.Mock]] = None):
    """
    Return a fake requests.request for a repository with README.md, a link, docs/, and scripts/run.sh, an executable.

    :param overrides: Responses that replace the defaults, by (method, path after the repository's api url).
    """
    root = tree(
        ROOT_TREE_SHA,
        [("README.md", "100644", "blob"), ("link", "120000", "blob"), ("docs", "040000", "tree")],
    )
    root["tree"].append({"path": "scripts", "mode": "040000", "type": "tree", "sha": SCRIPTS_TREE_SHA})
    routes = {
        ("GET", ""): response(200, {"default_branch": "main"}),
        ("GET", "/git/ref/heads/main"): response(200, {"object": {"sha": BASE_SHA}}),
        ("GET", "/git/ref/heads/alpha"): response(200, {"object": {"sha": BASE_SHA}}),
        ("GET", f"/git/commits/{BASE_SHA}"): response(200, {"sha": BASE_SHA, "tree": {"sha": ROOT_TREE_SHA}}),
        ("GET", f"/git/trees/{ROOT_TREE_SHA}"): response(200, root),
        ("GET", f"/git/trees/{SCRIPTS_TREE_SHA}"): response(
            200, tree(SCRIPTS_TREE_SHA, [("run.sh", "100755", "blob")])
        ),
        ("GET", "/git/trees/docs-sha"): response(200, tree("docs-sha", [("index.rst", "100644", "blob")])),
        ("POST", "/git/trees"): response(201, {"sha": NEW_TREE_SHA}),
        ("POST", "/git/commits"): response(201, {"sha": NEW_COMMIT_SHA}),
        ("POST", "/git/refs"): response(201, {"ref": "refs/heads/claude/fix", "object": {"sha": NEW_COMMIT_SHA}}),
        ("POST", "/pulls"): response(201, PULL),
    }
    routes.update(overrides or {})

    def request(method: str, url: str, **kwargs):
        assert url.startswith(API), url  # nosec B101: a test fake
        return routes[(method, url.removeprefix(API))]

    return request


class TestPullRequests(SmarterTestBase):
    """Test create_pull_request() and its validation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    def create(
        self,
        files: Optional[list[PullRequestFile]] = None,
        overrides: Optional[dict[tuple[str, str], mock.Mock]] = None,
        **kwargs,
    ) -> GitHubPullRequest:
        arguments = {
            "branch": "claude/fix",
            "title": "fix: the plugin timeout",
            "body": "Fixes #42.",
            "commit_message": "fix: the plugin timeout",
            "files": files or [PullRequestFile(path="README.md", content="new\n")],
            "token": SecretStr(TOKEN),
            **kwargs,
        }
        with mock.patch(REQUEST, side_effect=fake_github(overrides)) as request:
            self.request = request
            return create_pull_request(self.repository, **arguments)

    def sent(self, method: str, path: str) -> SmarterDictType:
        """Return the JSON body of the request that was sent to a path."""
        for call in self.request.call_args_list:
            if call.args == (method, f"{API}{path}"):
                return call.kwargs["json"]
        raise AssertionError(f"{method} {path} was not sent")

    def assert_fails(self, call, expected: str) -> str:
        with self.assertRaises(SmarterMCPServerToolError) as context:
            call()
        self.assertIn(expected, context.exception.message)
        self.assertNotIn(TOKEN, context.exception.message)
        return context.exception.message

    # -------------------------------------------------------------------------
    # validation
    # -------------------------------------------------------------------------
    def test_validate_branch(self):
        """Branch names that git accepts are accepted, and others refused."""
        for name in ("claude/fix-plugin-timeout", "alpha", "fix_1.2", "a"):
            with self.subTest(name=name):
                self.assertEqual(validate_branch(name), name)
        bad = ("", "-x", "/x", "x/", "x..y", "x//y", "x.lock", "x.", "x/.y", "x y", "x~1", "x" * 101, ".x")
        for name in bad:
            with self.subTest(name=name), self.assertRaisesRegex(SmarterMCPServerToolError, "not a valid branch"):
                validate_branch(name)

    def test_validate_files(self):
        """A change must be plain relative paths outside .github/ and .git/, each listed once, with content or delete."""
        good = [PullRequestFile(path="a/b.py", content=""), PullRequestFile(path="c.md", delete=True)]
        self.assertEqual(validate_files(good), good)
        many = [PullRequestFile(path=f"f{n}", content="x") for n in range(MAX_FILES + 1)]
        cases = [
            ([], "at least one file"),
            (many, f"at most {MAX_FILES} files"),
            ([PullRequestFile(path="/etc/passwd", content="x")], "not a path"),
            ([PullRequestFile(path="a/../b", content="x")], "not a path"),
            ([PullRequestFile(path="a/./b", content="x")], "not a path"),
            ([PullRequestFile(path="a//b", content="x")], "not a path"),
            ([PullRequestFile(path="a\\b", content="x")], "not a path"),
            ([PullRequestFile(path=".github/workflows/test.yml", content="x")], "never changes"),
            ([PullRequestFile(path=".git/config", content="x")], "never changes"),
            ([PullRequestFile(path="a", content="x"), PullRequestFile(path="a", content="y")], "listed twice"),
            ([PullRequestFile(path="a")], "either its whole new content"),
            ([PullRequestFile(path="a", content="x", delete=True)], "either its whole new content"),
        ]
        for files, expected in cases:
            with self.subTest(expected=expected, paths=[f.path for f in files][:2]):
                with self.assertRaisesRegex(SmarterMCPServerToolError, expected):
                    validate_files(files)

    def test_invalid_change_is_refused_before_github_is_contacted(self):
        """A bad token, branch, base, file or a credential is refused without a request."""
        api_key = "sk-" + "ant-" + "a1B2" * 8
        cases = [
            ({"token": None}, "personal access token"),
            ({"branch": "x..y"}, "not a valid branch"),
            ({"base": "x y"}, "not a valid branch"),
            ({"files": [PullRequestFile(path=".github/x.yml", content="x")]}, "never changes"),
            ({"files": [PullRequestFile(path="a.py", content=f"KEY = '{api_key}'")]}, "credential"),
            ({"body": f"token {TOKEN}"}, "caller's GitHub token"),
        ]
        for arguments, expected in cases:
            with self.subTest(expected=expected):
                message = self.assert_fails(lambda arguments=arguments: self.create(**arguments), expected)
                self.assertNotIn(api_key, message)
                self.request.assert_not_called()

    # -------------------------------------------------------------------------
    # create_pull_request
    # -------------------------------------------------------------------------
    def test_create_pull_request(self):
        """The change is one commit on a new branch from base, by its author, and the pull request is opened."""
        files = [
            PullRequestFile(path="README.md", content="new readme\n"),
            PullRequestFile(path="scripts/run.sh", content="#!/bin/sh\n"),
            PullRequestFile(path="docs/new/page.rst", content="Page\n"),
            PullRequestFile(path="scripts/old.sh", content="x"),
        ]
        author = GitHubCommitAuthor(name="Claude", email="noreply@anthropic.com")
        pull_request = self.create(files, base="alpha", author=author, draft=True)
        self.assertEqual(
            pull_request,
            GitHubPullRequest(
                number=7,
                title=PULL["title"],
                html_url=PULL["html_url"],
                draft=True,
                author="octocat",
                branch="claude/fix",
                base="alpha",
                commit_sha=NEW_COMMIT_SHA,
            ),
        )
        self.assertNotIn(("GET", API), [call.args for call in self.request.call_args_list])
        entries = self.sent("POST", "/git/trees")
        self.assertEqual(entries["base_tree"], ROOT_TREE_SHA)
        self.assertEqual(
            [(entry["path"], entry["mode"]) for entry in entries["tree"]],
            [
                ("README.md", "100644"),
                ("scripts/run.sh", "100755"),
                ("docs/new/page.rst", "100644"),
                ("scripts/old.sh", "100644"),
            ],
        )
        commit = self.sent("POST", "/git/commits")
        self.assertEqual(commit["tree"], NEW_TREE_SHA)
        self.assertEqual(commit["parents"], [BASE_SHA])
        self.assertEqual(commit["author"], {"name": "Claude", "email": "noreply@anthropic.com"})
        self.assertEqual(commit["committer"], commit["author"])
        self.assertEqual(self.sent("POST", "/git/refs"), {"ref": "refs/heads/claude/fix", "sha": NEW_COMMIT_SHA})
        self.assertEqual(
            self.sent("POST", "/pulls"),
            {
                "title": "fix: the plugin timeout",
                "head": "claude/fix",
                "base": "alpha",
                "body": "Fixes #42." + PULL_REQUEST_FOOTER,
                "draft": True,
            },
        )
        for call in self.request.call_args_list:
            self.assertEqual(call.kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        # each folder's tree is read once.
        tree_reads = [call for call in self.request.call_args_list if "/git/trees/" in call.args[1]]
        self.assertEqual(len(tree_reads), 3)

    def test_default_branch_and_author(self):
        """Without a base, the default branch is used, and without an author, GitHub uses the token's owner."""
        pull_request = self.create()
        self.assertEqual(pull_request.base, "main")
        self.assertIn(("GET", API), [call.args for call in self.request.call_args_list])
        commit = self.sent("POST", "/git/commits")
        self.assertNotIn("author", commit)
        self.assertNotIn("committer", commit)
        self.assertFalse(self.sent("POST", "/pulls")["draft"])

    def test_delete_a_file(self):
        """A deleted file keeps its mode, with no blob."""
        self.create([PullRequestFile(path="scripts/run.sh", delete=True)])
        self.assertEqual(
            self.sent("POST", "/git/trees")["tree"],
            [{"path": "scripts/run.sh", "mode": "100755", "type": "blob", "sha": None}],
        )

    def test_refused_changes(self):
        """A folder, a symbolic link, and the deletion of a file that does not exist are refused."""
        cases = [
            (PullRequestFile(path="docs", content="x"), "is a folder"),
            (PullRequestFile(path="link", content="x"), "symbolic link"),
            (PullRequestFile(path="nothing.md", delete=True), "does not exist"),
            (PullRequestFile(path="README.md/x", delete=True), "does not exist"),
        ]
        for file, expected in cases:
            with self.subTest(path=file.path):
                self.assert_fails(lambda file=file: self.create([file]), expected)
                self.assertNotIn(("POST", f"{API}/git/trees"), [call.args for call in self.request.call_args_list])

    def test_missing_base_branch(self):
        """A base branch that does not exist is explained."""
        self.assert_fails(
            lambda: self.create(base="beta", overrides={("GET", "/git/ref/heads/beta"): response(404, None)}),
            "The branch beta was not found",
        )

    def test_existing_branch(self):
        """GitHub refuses a branch that exists, and the pull request is not opened."""
        exists = response(422, {"message": "Reference already exists"})
        self.assert_fails(
            lambda: self.create(overrides={("POST", "/git/refs"): exists}),
            "could not create the branch claude/fix: Reference already exists",
        )
        self.assertNotIn(("POST", f"{API}/pulls"), [call.args for call in self.request.call_args_list])

    def test_pull_request_refused_after_the_branch_was_created(self):
        """When the pull request is refused, the error points to the new branch, and says not to try again."""
        refused = response(422, {"message": "No commits between main and claude/fix"})
        message = self.assert_fails(lambda: self.create(overrides={("POST", "/pulls"): refused}), "was created")
        self.assertIn("github.com/smarter-sh/smarter-test/tree/claude/fix", message)
        self.assertIn("No commits between", message)
        self.assertIn("Do not call create_pull_request again", message)

    def test_unreadable_responses(self):
        """A step whose response cannot be read is an error, and so is an unreadable pull request."""
        self.assert_fails(
            lambda: self.create(overrides={("POST", "/git/trees"): response(201, {"x": 1})}),
            "the new tree could not be read",
        )
        self.assert_fails(
            lambda: self.create(overrides={("POST", "/pulls"): response(201, {"number": "x"})}),
            "github.com/smarter-sh/smarter-test/pulls",
        )
        self.assert_fails(lambda: self.create(overrides={("POST", "/pulls"): response(201, None)}), "could not be read")

    def test_pull_request_without_a_user(self):
        """A pull request whose response has no user has no author."""
        self.assertIsNone(self.create(overrides={("POST", "/pulls"): response(201, {**PULL, "user": None})}).author)

    def test_the_token_is_never_logged(self):
        """Neither success nor failure logs the token."""
        for overrides in ({}, {("POST", "/pulls"): response(401, {"message": "Bad credentials"})}):
            with self.subTest(overrides=list(overrides)), mock.patch.object(pulls, "logger") as logger:
                try:
                    self.create(overrides=overrides)
                except SmarterMCPServerToolError:
                    pass
                self.assertNotIn(TOKEN, str(logger.method_calls))
