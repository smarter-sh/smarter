# pylint: disable=too-many-public-methods,unused-argument
"""
Unit tests for :py:mod:`smarter.apps.plugin.plugin.skill_sources`, the retrieval of remote.

Agent Skills.

Remote hosts are simulated by :class:`FakeSkillHost`, which serves ``./data/skill-remote``
as a skill in the fictitious GitHub repository example-org/skills. The live tests, which
retrieve a skill from Anthropic's https://github.com/anthropics/skills repository, are
skipped if GitHub is not reachable.
"""

import socket
from unittest import mock, skipUnless

import requests

from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    MAX_RESOURCES,
    SkillDocumentError,
)
from smarter.apps.plugin.manifest.models.skill_plugin.source import (
    SkillSourceError,
    parse_source_url,
)
from smarter.apps.plugin.plugin.skill_sources import (
    MAX_REDIRECTS,
    fetch,
    fetch_text,
    list_github_skill_files,
    retrieve_skill,
    validate_public_https_url,
)
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import (
    SKILL_REMOTE_RAW_URL,
    SKILL_REMOTE_TREE_URL,
    SKILL_REMOTE_URL,
    SKILL_SOURCES_DNS_PATCH,
    SKILL_SOURCES_REQUESTS_PATCH,
    FakeSkillHost,
    mock_skill_host,
)

ANTHROPIC_SKILL_URL = "https://github.com/anthropics/skills/tree/main/skills/brand-guidelines"


def github_is_available() -> bool:
    """Return True if GitHub is reachable from this process."""
    try:
        return requests.head("https://raw.githubusercontent.com/", timeout=5).status_code < 500
    except requests.exceptions.RequestException:
        return False


GITHUB_AVAILABLE = github_is_available()


def resolves_to(*addresses):
    """Return a stand-in for socket.getaddrinfo that resolves every host to the given addresses."""

    def getaddrinfo(host, port, *args, **kwargs):
        return [
            (socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
            for address in addresses
        ]

    return getaddrinfo


class TestSkillSources(SmarterTestBase):
    """Test the retrieval of remote skills."""

    # =========================================================================
    # validate_public_https_url()
    # =========================================================================
    def test_public_address(self):
        """Test that a host with a public address is allowed."""
        with mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=resolves_to("140.82.112.3", "2606:50c0:8000::154")):
            validate_public_https_url("https://raw.githubusercontent.com/a/b/main/SKILL.md")

    def test_non_public_addresses(self):
        """Test that hosts resolving to loopback, private, link-local and other non-public addresses are rejected."""
        for address in (
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
            "169.254.169.254",
            "100.64.0.1",
            # test data: an address that must be rejected. nothing binds to it.
            "0.0.0.0",  # nosec B104
            "::1",
            "fe80::1",
            "fd00::1",
            "::ffff:127.0.0.1",
        ):
            with mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=resolves_to(address)):
                with self.assertRaises(SkillSourceError, msg=f"address={address}"):
                    validate_public_https_url("https://example.com/SKILL.md")

    def test_any_non_public_address_is_rejected(self):
        """Test that a host is rejected if any one of its addresses is not public."""
        with mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=resolves_to("140.82.112.3", "10.0.0.1")):
            with self.assertRaises(SkillSourceError):
                validate_public_https_url("https://example.com/SKILL.md")

    def test_unresolvable_host(self):
        """Test that a host that cannot be resolved is rejected."""
        with mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=socket.gaierror("no such host")):
            with self.assertRaises(SkillSourceError):
                validate_public_https_url("https://no-such-host.example/SKILL.md")

    def test_non_https_url(self):
        """Test that URLs other than https are rejected, without resolving the host."""
        with mock.patch(SKILL_SOURCES_DNS_PATCH) as getaddrinfo:
            for url in ("http://example.com/SKILL.md", "ftp://example.com/SKILL.md", "https:///SKILL.md"):
                with self.assertRaises(SkillSourceError, msg=f"url={url}"):
                    validate_public_https_url(url)
        getaddrinfo.assert_not_called()

    # =========================================================================
    # fetch() and fetch_text()
    # =========================================================================
    def test_fetch(self):
        """Test downloading a file."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", b"# A")
        with mock_skill_host(host):
            self.assertEqual(fetch("https://example.com/a.md"), b"# A")

    def test_fetch_not_found(self):
        """Test that a response other than 200 OK raises."""
        for status_code in (404, 403, 500):
            host = FakeSkillHost()
            host.add("https://example.com/a.md", b"error", status_code=status_code)
            with mock_skill_host(host):
                with self.assertRaises(SkillSourceError, msg=f"status_code={status_code}"):
                    fetch("https://example.com/a.md")

    def test_fetch_too_large(self):
        """Test that a response larger than the limit raises."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", b"x" * 1001)
        with mock_skill_host(host):
            self.assertEqual(len(fetch("https://example.com/a.md", max_bytes=1001)), 1001)
            with self.assertRaises(SkillSourceError):
                fetch("https://example.com/a.md", max_bytes=1000)

    def test_fetch_follows_redirects(self):
        """Test that redirects, including relative ones, are followed."""
        host = FakeSkillHost()
        host.add("https://example.com/old.md", status_code=301, headers={"Location": "https://example.org/new.md"})
        host.add("https://example.org/new.md", status_code=302, headers={"Location": "/newest.md"})
        host.add("https://example.org/newest.md", b"# Newest")
        with mock_skill_host(host):
            self.assertEqual(fetch("https://example.com/old.md"), b"# Newest")
        self.assertEqual(
            host.requested,
            ["https://example.com/old.md", "https://example.org/new.md", "https://example.org/newest.md"],
        )

    def test_fetch_redirect_to_non_https(self):
        """Test that a redirect to a URL other than https is rejected."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", status_code=302, headers={"Location": "http://example.com/a.md"})
        with mock_skill_host(host):
            with self.assertRaises(SkillSourceError):
                fetch("https://example.com/a.md")

    def test_fetch_redirect_to_private_address(self):
        """Test that each redirect is validated, so that a redirect cannot reach a private address."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", status_code=302, headers={"Location": "https://internal.example/a.md"})

        def getaddrinfo(hostname, port, *args, **kwargs):
            address = "10.0.0.1" if hostname == "internal.example" else "140.82.112.3"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

        with mock_skill_host(host), mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=getaddrinfo):
            with self.assertRaises(SkillSourceError):
                fetch("https://example.com/a.md")
        self.assertNotIn("https://internal.example/a.md", host.requested)

    def test_fetch_too_many_redirects(self):
        """Test that a redirect loop is abandoned."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", status_code=302, headers={"Location": "https://example.com/a.md"})
        with mock_skill_host(host):
            with self.assertRaises(SkillSourceError):
                fetch("https://example.com/a.md")
        self.assertEqual(len(host.requested), MAX_REDIRECTS + 1)

    def test_fetch_request_exception(self):
        """Test that network errors are raised as a SkillSourceError."""
        with mock.patch(SKILL_SOURCES_DNS_PATCH, side_effect=resolves_to("140.82.112.3")):
            for error in (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                with (
                    mock.patch(SKILL_SOURCES_REQUESTS_PATCH, side_effect=error("boom")),
                    self.assertRaises(SkillSourceError, msg=f"error={error.__name__}"),
                ):
                    fetch("https://example.com/a.md")

    def test_fetch_does_not_follow_redirects_itself(self):
        """Test that requests are made without automatic redirects, streaming, and with a timeout."""
        with (
            mock_skill_host() as host,
            mock.patch(SKILL_SOURCES_REQUESTS_PATCH, side_effect=host.request) as get,
        ):
            fetch(SKILL_REMOTE_RAW_URL + "SKILL.md")
        kwargs = get.call_args.kwargs
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(kwargs["stream"])
        self.assertGreater(kwargs["timeout"], 0)

    def test_fetch_text(self):
        """Test downloading a UTF-8 text file."""
        host = FakeSkillHost()
        host.add("https://example.com/a.md", "Café ☕".encode())
        with mock_skill_host(host):
            self.assertEqual(fetch_text("https://example.com/a.md"), "Café ☕")

    def test_fetch_text_binary(self):
        """Test that binary files have no text contents."""
        host = FakeSkillHost()
        host.add("https://example.com/a.png", b"\x89PNG\r\n\x1a\n\x00\x00")
        host.add("https://example.com/b.bin", b"\xff\xfe\xfd")
        with mock_skill_host(host):
            self.assertIsNone(fetch_text("https://example.com/a.png"))
            self.assertIsNone(fetch_text("https://example.com/b.bin"))

    # =========================================================================
    # list_github_skill_files()
    # =========================================================================
    def test_list_github_skill_files(self):
        """Test listing the files beneath a skill directory, excluding SKILL.md and other directories."""
        with mock_skill_host():
            files = list_github_skill_files(parse_source_url(SKILL_REMOTE_URL))
        self.assertEqual(
            [path for path, _ in files],
            ["LICENSE.txt", "assets/logo.png", "forms.md", "reference.md", "scripts/fill_form.py"],
        )
        self.assertTrue(all(size > 0 for _, size in files))

    def test_list_github_skill_files_missing_skill(self):
        """Test that a directory without SKILL.md is rejected."""
        with mock_skill_host():
            with self.assertRaises(SkillSourceError):
                list_github_skill_files(
                    parse_source_url("https://github.com/example-org/skills/tree/main/skills/nothing-here")
                )

    def test_list_github_skill_files_not_found(self):
        """Test that a repository or ref that does not exist is rejected."""
        host = FakeSkillHost()
        host.remove(SKILL_REMOTE_TREE_URL)
        with mock_skill_host(host):
            with self.assertRaises(SkillSourceError):
                list_github_skill_files(parse_source_url(SKILL_REMOTE_URL))

    def test_list_github_skill_files_invalid_listing(self):
        """Test that an invalid tree listing is rejected."""
        for content in (b"not json", b"[]", json.dumps({"tree": "nope"}).encode("utf-8")):
            host = FakeSkillHost()
            host.add(SKILL_REMOTE_TREE_URL, content)
            with mock_skill_host(host):
                with self.assertRaises(SkillSourceError, msg=f"content={content!r}"):
                    list_github_skill_files(parse_source_url(SKILL_REMOTE_URL))

    def test_list_github_skill_files_does_not_match_directory_prefixes(self):
        """Test that a sibling directory whose name begins with the skill's name is not included."""
        host = FakeSkillHost()
        tree = json.loads(host.routes[SKILL_REMOTE_TREE_URL][0])
        tree["tree"].append({"path": "skills/test-skill-other/secret.md", "type": "blob", "size": 1})
        host.add(SKILL_REMOTE_TREE_URL, json.dumps(tree).encode("utf-8"))
        with mock_skill_host(host):
            paths = [path for path, _ in list_github_skill_files(parse_source_url(SKILL_REMOTE_URL))]
        self.assertNotIn("secret.md", paths)
        self.assertFalse(any("test-skill-other" in path for path in paths))

    # =========================================================================
    # retrieve_skill(): GitHub
    # =========================================================================
    def test_retrieve_github_skill(self):
        """Test retrieving a skill and all of its bundled files from GitHub."""
        with mock_skill_host():
            skill = retrieve_skill(SKILL_REMOTE_URL)
        self.assertEqual(skill.document.name, "test-skill")
        self.assertEqual(skill.location.url, SKILL_REMOTE_URL)
        self.assertEqual(
            list(skill.resources),
            ["LICENSE.txt", "assets/logo.png", "forms.md", "reference.md", "scripts/fill_form.py"],
        )
        self.assertTrue(skill.resources["forms.md"].startswith("# Forms"))  # type: ignore[union-attr]
        self.assertIsNone(skill.resources["assets/logo.png"])
        self.assertIsNotNone(skill.retrieved_at)

    def test_retrieve_github_skill_from_blob_and_raw_urls(self):
        """Test that the blob and raw URLs of SKILL.md retrieve the same skill as the directory URL."""
        with mock_skill_host():
            expected = retrieve_skill(SKILL_REMOTE_URL)
            for url in (
                "https://github.com/example-org/skills/blob/main/skills/test-skill/SKILL.md",
                SKILL_REMOTE_RAW_URL + "SKILL.md",
            ):
                skill = retrieve_skill(url)
                self.assertEqual(skill.document.document, expected.document.document, url)
                self.assertEqual(skill.resources, expected.resources, url)

    def test_retrieve_github_skill_missing_skill_md(self):
        """Test that a listed skill whose SKILL.md cannot be downloaded is rejected."""
        host = FakeSkillHost()
        host.remove(SKILL_REMOTE_RAW_URL + "SKILL.md")
        with mock_skill_host(host):
            with self.assertRaises(SkillSourceError):
                retrieve_skill(SKILL_REMOTE_URL)

    def test_retrieve_github_skill_invalid_skill_md(self):
        """Test that an invalid SKILL.md is rejected."""
        host = FakeSkillHost()
        host.add(SKILL_REMOTE_RAW_URL + "SKILL.md", b"# no frontmatter")
        with mock_skill_host(host):
            with self.assertRaises(SkillDocumentError):
                retrieve_skill(SKILL_REMOTE_URL)

    def test_retrieve_github_skill_binary_skill_md(self):
        """Test that a SKILL.md that is not text is rejected."""
        host = FakeSkillHost()
        host.add(SKILL_REMOTE_RAW_URL + "SKILL.md", b"\x00\x01\x02")
        with mock_skill_host(host):
            with self.assertRaises(SkillSourceError):
                retrieve_skill(SKILL_REMOTE_URL)

    def test_retrieve_github_skill_unavailable_resource(self):
        """Test that a listed bundled file that cannot be downloaded is recorded without contents."""
        host = FakeSkillHost()
        host.remove(SKILL_REMOTE_RAW_URL + "reference.md")
        with mock_skill_host(host):
            skill = retrieve_skill(SKILL_REMOTE_URL)
        self.assertIn("reference.md", skill.resources)
        self.assertIsNone(skill.resources["reference.md"])

    def test_retrieve_github_skill_too_many_resources(self):
        """Test that at most MAX_RESOURCES bundled files are retrieved."""
        host = FakeSkillHost()
        tree = json.loads(host.routes[SKILL_REMOTE_TREE_URL][0])
        for i in range(MAX_RESOURCES + 10):
            path = f"references/{i:03}.md"
            tree["tree"].append({"path": f"skills/test-skill/{path}", "type": "blob", "size": 3})
            host.add(SKILL_REMOTE_RAW_URL + path, b"# x")
        host.add(SKILL_REMOTE_TREE_URL, json.dumps(tree).encode("utf-8"))
        with mock_skill_host(host):
            skill = retrieve_skill(SKILL_REMOTE_URL)
        self.assertEqual(len(skill.resources), MAX_RESOURCES)

    def test_retrieve_github_skill_oversized_resource_is_not_downloaded(self):
        """Test that a bundled file listed as too large is recorded without contents, and not downloaded."""
        host = FakeSkillHost()
        tree = json.loads(host.routes[SKILL_REMOTE_TREE_URL][0])
        tree["tree"].append({"path": "skills/test-skill/assets/huge.bin", "type": "blob", "size": 50_000_000})
        host.add(SKILL_REMOTE_TREE_URL, json.dumps(tree).encode("utf-8"))
        with mock_skill_host(host):
            skill = retrieve_skill(SKILL_REMOTE_URL)
        self.assertIsNone(skill.resources["assets/huge.bin"])
        self.assertNotIn(SKILL_REMOTE_RAW_URL + "assets/huge.bin", host.requested)

    def test_retrieve_github_skill_makes_one_api_request(self):
        """Test that one GitHub api request is made per skill, since the api is rate limited."""
        with mock_skill_host() as host:
            retrieve_skill(SKILL_REMOTE_URL)
        self.assertEqual(len([url for url in host.requested if url.startswith("https://api.github.com/")]), 1)

    # =========================================================================
    # retrieve_skill(): other https hosts
    # =========================================================================
    def test_retrieve_generic_skill(self):
        """Test retrieving a skill from a host other than GitHub, along with the files it links to."""
        host = FakeSkillHost()
        host.add(
            "https://skills.example.com/meeting-notes/SKILL.md",
            b"---\nname: meeting-notes\ndescription: Takes notes. Use for meetings.\n---\n"
            b"Use [the template](assets/template.md) and `scripts/run.py`. See `examples.md`.\n",
        )
        host.add("https://skills.example.com/meeting-notes/assets/template.md", b"# Template")
        host.add("https://skills.example.com/meeting-notes/scripts/run.py", b"print(1)")
        with mock_skill_host(host):
            skill = retrieve_skill("https://skills.example.com/meeting-notes/SKILL.md")
        self.assertEqual(skill.document.name, "meeting-notes")
        # examples.md could not be downloaded, and so is not a bundled file
        self.assertEqual(skill.resources, {"assets/template.md": "# Template", "scripts/run.py": "print(1)"})
        self.assertFalse(any(url.startswith("https://api.github.com/") for url in host.requested))

    def test_retrieve_generic_skill_not_found(self):
        """Test that a SKILL.md that cannot be downloaded is rejected."""
        with mock_skill_host():
            with self.assertRaises(SkillSourceError):
                retrieve_skill("https://skills.example.com/nothing-here/SKILL.md")

    def test_retrieve_invalid_url(self):
        """Test that an unsupported URL is rejected without any request."""
        with mock_skill_host() as host:
            with self.assertRaises(SkillSourceError):
                retrieve_skill("http://example.com/SKILL.md")
        self.assertEqual(host.requested, [])

    def test_retrieve_skill_name_mismatch_is_tolerated(self):
        """Test that a skill whose name does not match its directory is retrieved, with a warning."""
        host = FakeSkillHost()
        host.add(
            SKILL_REMOTE_RAW_URL + "SKILL.md",
            b"---\nname: a-different-name\ndescription: A skill. Use when testing.\n---\nbody\n",
        )
        with mock_skill_host(host):
            self.assertEqual(retrieve_skill(SKILL_REMOTE_URL).document.name, "a-different-name")

    # =========================================================================
    # live: Anthropic's skills repository
    # =========================================================================
    @skipUnless(GITHUB_AVAILABLE, "GitHub is not reachable")
    def test_live_retrieve_anthropic_skill(self):
        """Test retrieving a real skill from Anthropic's skills repository."""
        skill = retrieve_skill(ANTHROPIC_SKILL_URL)
        self.assertEqual(skill.document.name, "brand-guidelines")
        self.assertTrue(skill.document.description)
        self.assertTrue(skill.document.body)
        self.assertIn("LICENSE.txt", skill.resources)
