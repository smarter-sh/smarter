"""Test the source code repository helpers, :mod:`smarter.common.utils.repository`."""

import subprocess
from unittest.mock import patch

from smarter.common.const import SMARTER_PROJECT_REPOSITORY_URL
from smarter.common.utils import repository
from smarter.common.utils.repository import (
    get_repository_url,
    normalize_remote_url,
    parse_git_remotes,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

UPSTREAM = "https://github.com/smarter-sh/smarter"


class TestRepository(SmarterTestBase):
    """Test normalize_remote_url(), parse_git_remotes() and get_repository_url()."""

    def setUp(self):
        super().setUp()
        get_repository_url.cache_clear()
        self.addCleanup(get_repository_url.cache_clear)

    def test_normalize_https(self):
        """An https remote loses its .git suffix and trailing slash."""
        self.assertEqual(normalize_remote_url("https://github.com/smarter-sh/smarter.git"), UPSTREAM)
        self.assertEqual(normalize_remote_url("https://github.com/smarter-sh/smarter/"), UPSTREAM)
        self.assertEqual(normalize_remote_url("http://github.com/smarter-sh/smarter"), UPSTREAM)

    def test_normalize_ssh(self):
        """Both forms of ssh remote become https."""
        self.assertEqual(normalize_remote_url("git@github.com:smarter-sh/smarter.git"), UPSTREAM)
        self.assertEqual(normalize_remote_url("ssh://git@github.com:22/smarter-sh/smarter.git"), UPSTREAM)
        self.assertEqual(normalize_remote_url("git://github.com/smarter-sh/smarter.git"), UPSTREAM)

    def test_normalize_any_host(self):
        """A remote on any host is kept on that host, with an https remote's port."""
        self.assertEqual(
            normalize_remote_url("git@bitbucket.org:someone/smarter.git"), "https://bitbucket.org/someone/smarter"
        )
        self.assertEqual(
            normalize_remote_url("https://gitlab.com/group/subgroup/smarter.git"),
            "https://gitlab.com/group/subgroup/smarter",
        )
        self.assertEqual(
            normalize_remote_url("https://git.example.com:8443/smarter.git"), "https://git.example.com:8443/smarter"
        )

    def test_normalize_removes_credentials(self):
        """A token embedded in the remote never reaches the browser."""
        self.assertEqual(
            normalize_remote_url("https://user:not-a-real-token@github.com/smarter-sh/smarter.git"), UPSTREAM
        )
        self.assertEqual(normalize_remote_url("https://x-access-token@github.com/smarter-sh/smarter"), UPSTREAM)

    def test_normalize_rejects_what_a_browser_cannot_open(self):
        """A local path, an unknown scheme, or a remote without a path, is not a repository url."""
        self.assertIsNone(normalize_remote_url("/srv/git/smarter.git"))
        self.assertIsNone(normalize_remote_url("file:///srv/git/smarter.git"))
        self.assertIsNone(normalize_remote_url("https://github.com/"))
        self.assertIsNone(normalize_remote_url("https://github.com/.git"))

    def test_parse_prefers_origin(self):
        """The origin remote's fetch url wins, wherever it is listed."""
        output = (
            "fork\thttps://github.com/someone/smarter.git (fetch)\n"
            "fork\thttps://github.com/someone/smarter.git (push)\n"
            "origin\tgit@github.com:smarter-sh/smarter.git (fetch)\n"
            "origin\tgit@github.com:smarter-sh/smarter.git (push)\n"
        )
        self.assertEqual(parse_git_remotes(output), UPSTREAM)

    def test_parse_without_origin(self):
        """Without an origin, the first usable fetch url wins."""
        output = "local\t/srv/git/smarter.git (fetch)\nfork\thttps://github.com/someone/smarter.git (fetch)\n"
        self.assertEqual(parse_git_remotes(output), "https://github.com/someone/smarter")

    def test_parse_nothing(self):
        """No remote, or only push urls, is no url."""
        self.assertIsNone(parse_git_remotes(""))
        self.assertIsNone(parse_git_remotes("origin\thttps://github.com/smarter-sh/smarter.git (push)\n"))

    def test_get_repository_url_from_git(self):
        """The url comes from git remote -v, run in the repository's root."""
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="origin\thttps://github.com/someone/smarter.git (fetch)\n"
        )
        with patch.object(repository.subprocess, "run", return_value=completed) as run:
            self.assertEqual(get_repository_url(), "https://github.com/someone/smarter")
        self.assertEqual(run.call_args.args[0], ["git", "remote", "-v"])
        self.assertEqual(run.call_args.kwargs["cwd"], repository.REPO_ROOT)

    def test_get_repository_url_without_git(self):
        """Without a .git directory, as in the Docker image, or without git, the default is used."""
        failure = subprocess.CalledProcessError(128, ["git", "remote", "-v"])
        with patch.object(repository.subprocess, "run", side_effect=failure):
            self.assertEqual(get_repository_url(), SMARTER_PROJECT_REPOSITORY_URL)
        get_repository_url.cache_clear()
        with patch.object(repository.subprocess, "run", side_effect=FileNotFoundError("git")):
            self.assertEqual(get_repository_url(), SMARTER_PROJECT_REPOSITORY_URL)

    def test_get_repository_url_without_remotes(self):
        """A repository without a usable remote gets the default."""
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        with patch.object(repository.subprocess, "run", return_value=completed):
            self.assertEqual(get_repository_url(), SMARTER_PROJECT_REPOSITORY_URL)
